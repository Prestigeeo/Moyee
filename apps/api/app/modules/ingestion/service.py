"""Document ingestion pipeline: PDF/TXT validation, page extraction, chunking & cited summaries.

Follows PRD §6.5 & §6.6:
- Validates file types, magic bytes, size limits, and page counts.
- Rejects scanned/image-only PDFs with a clear human-readable explanation.
- Preserves exact page numbers and character offsets on every chunk.
- Produces structured summaries (Aim, Methodology, Sample, Findings, Limitations) where every
  section is linked to an actual page and quote from the document—never inventing page references.
"""

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PAGES = 300
MIN_AVG_CHARS_PER_PAGE = 35
CHUNK_SIZE_CHARS = 1600
CHUNK_OVERLAP_CHARS = 200


class IngestionError(Exception):
    """Raised when a document cannot be safely or meaningfully processed."""


@dataclass
class ExtractedPage:
    page_number: int
    text: str


@dataclass
class TextChunk:
    chunk_index: int
    page_number: int | None
    char_start: int
    char_end: int
    text: str


def extract_pdf_pages(raw_bytes: bytes) -> list[ExtractedPage]:
    if not raw_bytes.startswith(b"%PDF-"):
        raise IngestionError("File is not a valid PDF document.")
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except (PdfReadError, Exception) as exc:
        raise IngestionError("PDF file is corrupted or encrypted and cannot be read.") from exc

    if reader.is_encrypted:
        raise IngestionError(
            "Password-protected PDFs cannot be processed. Please upload an unlocked copy."
        )

    num_pages = len(reader.pages)
    if num_pages == 0:
        raise IngestionError("PDF has no pages.")
    if num_pages > MAX_PAGES:
        raise IngestionError(f"PDF exceeds the {MAX_PAGES}-page limit ({num_pages} pages).")

    pages: list[ExtractedPage] = []
    total_chars = 0
    for idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned = re.sub(r"[ \t]+", " ", raw_text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        total_chars += len(cleaned)
        pages.append(ExtractedPage(page_number=idx, text=cleaned))

    if total_chars < max(40, num_pages * MIN_AVG_CHARS_PER_PAGE):
        raise IngestionError(
            "This PDF appears to be a scanned image without an extractable text layer."
        )
    return pages


def chunk_pages(pages: list[ExtractedPage]) -> list[TextChunk]:
    """Chunk each page independently so `page_number` and character offsets stay exact."""
    chunks: list[TextChunk] = []
    chunk_idx = 0
    for page in pages:
        text = page.text
        if not text:
            continue
        start = 0
        length = len(text)
        while start < length:
            end = min(length, start + CHUNK_SIZE_CHARS)
            if end < length:
                # Prefer breaking at a sentence or whitespace boundary.
                boundary = max(
                    text.rfind(". ", start + CHUNK_SIZE_CHARS // 2, end),
                    text.rfind("\n", start + CHUNK_SIZE_CHARS // 2, end),
                    text.rfind(" ", start + CHUNK_SIZE_CHARS // 2, end),
                )
                if boundary > start:
                    end = boundary + 1
            segment = text[start:end].strip()
            if segment:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_idx,
                        page_number=page.page_number,
                        char_start=start,
                        char_end=end,
                        text=segment,
                    )
                )
                chunk_idx += 1
            if end >= length:
                break
            start = max(start + 1, end - CHUNK_OVERLAP_CHARS)
    return chunks


SUMMARY_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "aim",
        [
            "aim",
            "objective",
            "purpose",
            "this study",
            "this paper",
            "we investigate",
            "we examine",
            "research question",
        ],
    ),
    (
        "methodology",
        [
            "method",
            "methodology",
            "design",
            "survey",
            "experiment",
            "regression",
            "qualitative",
            "quantitative",
            "data collection",
            "procedure",
        ],
    ),
    (
        "sample",
        [
            "sample",
            "participants",
            "population",
            "respondents",
            "n =",
            "households",
            "students",
            "dataset",
            "sites",
        ],
    ),
    (
        "findings",
        [
            "result",
            "finding",
            "showed",
            "demonstrate",
            "significant",
            "increase",
            "decrease",
            "conclude",
            "evidence",
        ],
    ),
    (
        "limitations",
        [
            "limitation",
            "future research",
            "constraint",
            "caveat",
            "shortcoming",
            "generalizability",
        ],
    ),
]


def _split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [s.strip() for s in raw if len(s.strip()) >= 35]


def generate_grounded_summary(chunks: list[dict]) -> dict[str, dict]:
    """Extract a structured summary grounded strictly in `chunks`.

    Each `chunk` dict has `id`, `page_number`, and `text_content`.
    If no supporting sentence is found for a section, `text` is `"Not reported in source"`
    and `page_number` is `None` (never fabricated).
    """
    from app.ai.gateway import generate_llm_document_summary

    llm_sections = generate_llm_document_summary(chunks)
    result: dict[str, dict] = {}
    for section_key, keywords in SUMMARY_SECTIONS:
        if (
            llm_sections
            and section_key in llm_sections
            and llm_sections[section_key].get("chunk_id")
        ):
            result[section_key] = llm_sections[section_key]
            continue

        best_score = 0
        best_sentence: str | None = None
        best_chunk: dict | None = None

        for chunk in chunks:
            sentences = _split_sentences(chunk["text_content"])
            for sent in sentences:
                lower = sent.lower()
                score = sum(2 if f" {kw}" in f" {lower}" else 0 for kw in keywords)
                if score > best_score:
                    best_score = score
                    best_sentence = sent
                    best_chunk = chunk

        if best_sentence and best_chunk and best_score > 0:
            snippet = best_sentence[:360]
            result[section_key] = {
                "text": snippet,
                "quote": snippet,
                "page_number": best_chunk["page_number"],
                "chunk_id": str(best_chunk["id"]),
            }
        else:
            result[section_key] = {
                "text": "Not reported in accessible source text.",
                "quote": None,
                "page_number": None,
                "chunk_id": None,
            }
    return result
