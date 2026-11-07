"""Literature Review & Synthesis Studio service (PRD §6.8).

- Extracts structured comparative fields per source with page-level evidence references.
- Marks missing information as 'Not reported' rather than fabricating claims.
- Preserves user edits (`user_edited = True`, clearing stale citations).
- Generates cross-study synthesis (themes, methodological comparison, and potential gaps
  explicitly labelled as requiring human verification).
- Exports the matrix to CSV.
"""

import csv
import io
import re
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from docx import Document as DocxDocument
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.gateway import generate_llm_matrix_cells, generate_llm_matrix_synthesis
from app.modules.billing import service as billing
from app.modules.library.models import DocumentChunk, ProjectSource
from app.modules.literature.models import LiteratureEntry, LiteratureMatrix
from app.modules.literature.schemas import (
    MatrixCellOut,
    MatrixCellUpdateRequest,
    MatrixCreate,
    MatrixDetailOut,
    MatrixEntryOut,
    MatrixSummaryOut,
    SynthesisNotesOut,
    SynthesisThemeOut,
)
from app.modules.projects.models import Project
from app.modules.references.formatter import format_inline_citation
from app.modules.retrieval.service import tokenize

MATRIX_FIELD_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "aim",
        [
            "current study aims",
            "this study aims",
            "this study examines",
            "this study investigates",
            "study addresses",
            "aim",
            "objective",
            "purpose",
            "this study",
            "examine",
            "investigate",
        ],
    ),
    (
        "methodology",
        [
            "study adopted",
            "quasi-experimental",
            "quasi experimental",
            "cross-sectional",
            "research design",
            "methodology",
            "qualitative",
            "quantitative",
            "mixed methods",
            "mixed",
            "panel",
            "experiment",
        ],
    ),
    (
        "sample",
        [
            "participants",
            "sample was drawn",
            "enrolled in",
            "sample",
            "population",
            "respondents",
            "n =",
            "households",
            "learners",
            "undergraduate",
            "students",
        ],
    ),
    (
        "data_collection",
        [
            "questionnaire",
            "survey",
            "interview",
            "data collection",
            "collected",
            "instrument",
            "dataset",
            "records",
            "satellite",
            "observations",
        ],
    ),
    (
        "analysis",
        [
            "anova",
            "t-test",
            "spss",
            "descriptive statistical",
            "regression",
            "correlation",
            "thematic",
            "statistical",
            "coding",
            "model",
            "estimated",
        ],
    ),
    (
        "findings",
        [
            "our findings show",
            "results showed",
            "results of study",
            "findings reveal",
            "result",
            "finding",
            "showed",
            "significant",
            "increase",
            "decrease",
            "reduction",
            "adopted",
        ],
    ),
    (
        "limitations",
        [
            "limits the representativeness",
            "constrains the generalizability",
            "limitation",
            "limitations",
            "constraint",
            "future research",
            "caveat",
            "shortcoming",
            "horizon",
        ],
    ),
]

SYNTHESIS_STOPWORDS: set[str] = {
    "these",
    "those",
    "their",
    "there",
    "where",
    "which",
    "while",
    "within",
    "through",
    "between",
    "among",
    "across",
    "study",
    "studies",
    "paper",
    "papers",
    "article",
    "research",
    "results",
    "findings",
    "finding",
    "result",
    "using",
    "based",
    "however",
    "although",
    "furthermore",
    "moreover",
    "showed",
    "shown",
    "examined",
    "investigated",
    "participants",
    "students",
    "student",
    "learners",
    "group",
    "groups",
    "level",
    "levels",
    "other",
    "first",
    "second",
    "three",
    "under",
    "after",
    "before",
    "during",
}


def _clean_pdf_sentence(text: str, max_len: int = 300) -> str:
    """Repair common PDF intra-word spacing glitches and truncate on a clean word boundary."""
    s = re.sub(r"\s+", " ", text).strip()
    # Fix hyphen/dash spacing glitches like "AI -based" or "AI- enabled"
    s = re.sub(r"(\w)\s+-\s*(\w)", r"\1-\2", s)
    s = re.sub(r"(\w)-\s+(\w)", r"\1-\2", s)
    # Fix single capital letter split at start of word: "Q ualitative" -> "Qualitative"
    s = re.sub(r"\b([B-HJ-Z])\s+([a-z]{3,})\b", r"\1\2", s)
    # Strip leading numbering artifacts like "26) to ensure..."
    s = re.sub(r"^\d+\)\s*", "", s)
    if len(s) <= max_len:
        return s
    cut = s[: max_len - 1].rsplit(" ", 1)[0].rstrip(",;:")
    return f"{cut}…"


def _is_reference_chunk(text: str) -> bool:
    """Detect bibliography/reference-list chunks so we don't extract cited book titles."""
    lower = text.lower()
    if re.search(r"(^|\n)\s*(references|bibliography|works cited)\s*(\n|$)", lower):
        return True
    doi_hits = len(re.findall(r"https?://doi\.org/|doi:\s*10\.", lower))
    year_parens = len(re.findall(r"\(\d{4}[a-z]?\)\.", text))
    ed_hits = len(re.findall(r"\(\d+(?:st|nd|rd|th)\s+ed\.\)", lower))
    return doi_hits >= 2 or year_parens >= 3 or ed_hits >= 1


def _filter_non_reference_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    filtered = [c for c in chunks if not _is_reference_chunk(c.text_content)]
    return filtered if filtered else list(chunks)


def _extract_cells_from_chunks(
    project: Project, source: ProjectSource, raw_chunks: list[DocumentChunk]
) -> dict[str, dict]:
    chunks = _filter_non_reference_chunks(raw_chunks)

    chunk_dicts = [
        {
            "id": str(c.id),
            "page_number": c.page_number,
            "text_content": c.text_content,
        }
        for c in chunks
    ]
    llm_cells = generate_llm_matrix_cells(
        project_topic=project.topic,
        source_title=source.title,
        source_authors=source.authors,
        chunks=chunk_dicts,
    )

    cells: dict[str, dict] = {}
    used_sentences: set[str] = set()

    for field_key, keywords in MATRIX_FIELD_KEYWORDS:
        if llm_cells and field_key in llm_cells:
            llm_cell = llm_cells[field_key]
            val = _clean_pdf_sentence(llm_cell.get("value") or "Not reported", max_len=320)
            if val != "Not reported":
                cells[field_key] = {
                    "value": val,
                    "page_number": llm_cell.get("page_number"),
                    "quote": _clean_pdf_sentence(llm_cell.get("quote") or val, max_len=240)
                    if llm_cell.get("page_number")
                    else None,
                    "user_edited": False,
                }
                used_sentences.add(val.lower()[:120])
                continue

        best_score = 0
        best_sent: str | None = None
        best_page: int | None = None

        for chunk in chunks:
            sentences = [
                _clean_pdf_sentence(s, max_len=300)
                for s in re.split(r"(?<=[.!?])\s+", chunk.text_content.replace("\n", " "))
                if len(s.strip()) >= 28
            ]
            for sent in sentences:
                norm_key = sent.lower()[:120]
                if norm_key in used_sentences:
                    continue
                lower = sent.lower()
                score = sum(2 if kw in lower else 0 for kw in keywords)
                if score == 0:
                    continue
                # Boost own-study statements
                if any(
                    marker in lower
                    for marker in (
                        "this study",
                        "current study",
                        "our study",
                        "our findings",
                        "we ",
                        "study 1",
                        "results:",
                    )
                ):
                    score += 2
                # Penalize third-party literature citations like "Zhang (2025) demonstrated..."
                if re.search(r"\b[A-Z][a-z]+\s+(?:et al\.\s*)?\(\d{4}\)", sent):
                    score -= 3
                if "in their study" in lower or "ed.)" in lower:
                    score -= 4

                if score > best_score:
                    best_score = score
                    best_sent = sent
                    best_page = chunk.page_number

        if best_sent and best_score > 0:
            used_sentences.add(best_sent.lower()[:120])
            cells[field_key] = {
                "value": best_sent,
                "page_number": best_page,
                "quote": best_sent[:240],
                "user_edited": False,
            }
        else:
            cells[field_key] = {
                "value": "Not reported",
                "page_number": None,
                "quote": None,
                "user_edited": False,
            }

    if (
        llm_cells
        and "relevance" in llm_cells
        and llm_cells["relevance"].get("value") != "Not reported"
    ):
        cells["relevance"] = {
            "value": _clean_pdf_sentence(llm_cells["relevance"]["value"], max_len=280),
            "page_number": None,
            "quote": None,
            "user_edited": False,
        }
    else:
        topic_terms = set(tokenize(project.topic)) - SYNTHESIS_STOPWORDS
        raw_src_tokens = tokenize(f"{source.title} {source.abstract or ''}")
        source_terms = set(raw_src_tokens) - SYNTHESIS_STOPWORDS
        shared = sorted(topic_terms & source_terms)[:5]
        rel_text = (
            f"Addresses {', '.join(shared)} in relation to project topic."
            if shared
            else f"Saved as background literature for {project.name}."
        )
        cells["relevance"] = {
            "value": rel_text,
            "page_number": None,
            "quote": None,
            "user_edited": False,
        }
    return cells


def _build_synthesis(
    project: Project, entries: list[tuple[LiteratureEntry, ProjectSource]]
) -> dict:
    study_rows: list[dict] = []
    for idx, (entry, src) in enumerate(entries, start=1):
        label = format_inline_citation(src, project.citation_style, idx)
        study_rows.append(
            {
                "study": label,
                "title": src.title,
                "aim": (entry.cells.get("aim") or {}).get("value", "Not reported"),
                "methodology": (entry.cells.get("methodology") or {}).get("value", "Not reported"),
                "sample": (entry.cells.get("sample") or {}).get("value", "Not reported"),
                "findings": (entry.cells.get("findings") or {}).get("value", "Not reported"),
                "limitations": (entry.cells.get("limitations") or {}).get("value", "Not reported"),
            }
        )

    llm_synth = generate_llm_matrix_synthesis(
        project_topic=project.topic,
        study_rows=study_rows,
    )
    if llm_synth:
        return llm_synth

    term_sources: dict[str, list[str]] = {}
    methods_found: list[str] = []
    unreported_counts: Counter[str] = Counter()

    for idx, (entry, src) in enumerate(entries, start=1):
        label = format_inline_citation(src, project.citation_style, idx)
        tokens = set(tokenize(f"{src.title} {src.abstract or ''}"))
        for tok in tokens:
            if len(tok) >= 5 and tok not in SYNTHESIS_STOPWORDS:
                term_sources.setdefault(tok, [])
                if label not in term_sources[tok]:
                    term_sources[tok].append(label)

        method_val = (entry.cells.get("methodology") or {}).get("value", "Not reported")
        if method_val != "Not reported":
            methods_found.append(f"{label}: {method_val[:140]}")

        for key in ("sample", "limitations", "data_collection"):
            if (entry.cells.get(key) or {}).get("value") == "Not reported":
                unreported_counts[key] += 1

    ranked_terms = sorted(term_sources.items(), key=lambda kv: (len(kv[1]), kv[0]), reverse=True)[
        :4
    ]
    themes = [
        {
            "theme": f"{term.capitalize()} & Empirical Patterns",
            "sources": srcs,
            "summary": f"Examined across {len(srcs)} study(ies) ({', '.join(srcs)}).",
        }
        for term, srcs in ranked_terms
    ]

    method_comp = (
        " | ".join(methods_found)
        if methods_found
        else (
            "Methodological details were not reported in the accessible "
            "excerpts of the selected sources."
        )
    )

    gaps: list[str] = []
    if unreported_counts["limitations"] > 0:
        gaps.append(
            f"Potential gap (requires human verification): {unreported_counts['limitations']} of "
            f"{len(entries)} selected studies did not report explicit study limitations."
        )
    if unreported_counts["sample"] > 0:
        gaps.append(
            f"Potential gap (requires human verification): {unreported_counts['sample']} "
            "study(ies) lacked explicit sample/population details in the extracted text."
        )
    gaps.append(
        "Potential gap (requires human verification): Evaluate whether the "
        f"{len(entries)} compared studies cover the specific context of '{project.topic}'."
    )

    return {
        "themes": themes,
        "methodological_comparison": method_comp,
        "potential_gaps": gaps,
    }


def list_matrices(db: Session, project: Project) -> list[MatrixSummaryOut]:
    matrices = db.scalars(
        select(LiteratureMatrix)
        .where(
            LiteratureMatrix.project_id == project.id,
            LiteratureMatrix.owner_id == project.owner_id,
        )
        .order_by(LiteratureMatrix.updated_at.desc())
    ).all()
    out: list[MatrixSummaryOut] = []
    for m in matrices:
        cnt = (
            db.scalar(
                select(func.count())
                .select_from(LiteratureEntry)
                .where(LiteratureEntry.matrix_id == m.id)
            )
            or 0
        )
        out.append(
            MatrixSummaryOut(
                id=m.id,
                project_id=m.project_id,
                name=m.name,
                entry_count=cnt,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )
    return out


def get_owned_matrix(
    db: Session, owner_id: uuid.UUID, project_id: uuid.UUID, matrix_id: uuid.UUID
) -> LiteratureMatrix:
    m = db.scalar(
        select(LiteratureMatrix).where(
            LiteratureMatrix.id == matrix_id,
            LiteratureMatrix.project_id == project_id,
            LiteratureMatrix.owner_id == owner_id,
        )
    )
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Literature matrix not found"
        )
    return m


def _to_matrix_detail(db: Session, project: Project, matrix: LiteratureMatrix) -> MatrixDetailOut:
    rows = db.execute(
        select(LiteratureEntry, ProjectSource)
        .join(ProjectSource, LiteratureEntry.project_source_id == ProjectSource.id)
        .where(LiteratureEntry.matrix_id == matrix.id)
        .order_by(LiteratureEntry.created_at.asc())
    ).all()

    entries_out: list[MatrixEntryOut] = []
    for idx, (entry, src) in enumerate(rows, start=1):
        cells_out = {k: MatrixCellOut(**v) for k, v in (entry.cells or {}).items()}
        entries_out.append(
            MatrixEntryOut(
                id=entry.id,
                project_source_id=src.id,
                author_year=format_inline_citation(src, project.citation_style, idx),
                title=src.title,
                cells=cells_out,
                updated_at=entry.updated_at,
            )
        )

    notes_raw = matrix.synthesis_notes or {}
    notes_out = SynthesisNotesOut(
        themes=[SynthesisThemeOut(**t) for t in (notes_raw.get("themes") or [])],
        methodological_comparison=notes_raw.get("methodological_comparison", ""),
        potential_gaps=notes_raw.get("potential_gaps") or [],
    )
    return MatrixDetailOut(
        id=matrix.id,
        project_id=matrix.project_id,
        name=matrix.name,
        entries=entries_out,
        synthesis_notes=notes_out,
        created_at=matrix.created_at,
        updated_at=matrix.updated_at,
    )


def create_matrix(db: Session, project: Project, data: MatrixCreate) -> MatrixDetailOut:
    existing_count = (
        db.scalar(
            select(func.count())
            .select_from(LiteratureMatrix)
            .where(LiteratureMatrix.project_id == project.id)
        )
        or 0
    )
    billing.ensure_capacity(db, project.owner_id, "matrices_per_project", existing_count, 1)

    max_sources = billing.get_limit(db, project.owner_id, "matrix_sources") or 5
    unique_ids = list(dict.fromkeys(data.source_ids))
    if len(unique_ids) > max_sources:
        raise billing.QuotaExceeded("matrix_sources", max_sources, None)

    sources = list(
        db.scalars(
            select(ProjectSource).where(
                ProjectSource.project_id == project.id,
                ProjectSource.owner_id == project.owner_id,
                ProjectSource.id.in_(unique_ids),
            )
        ).all()
    )
    if not sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one valid project source.",
        )

    # 1. Load all chunks from DB first (never hold a DB transaction open during LLM calls)
    chunks_by_source: dict[uuid.UUID, list[DocumentChunk]] = {}
    for src in sources:
        chunks_by_source[src.id] = list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.project_source_id == src.id)
                .order_by(DocumentChunk.chunk_index)
            ).all()
        )

    # 2. Extract cells across all selected sources in parallel (~5s total instead of 35s)
    with ThreadPoolExecutor(max_workers=min(5, len(sources))) as pool:
        extracted_cells_list = list(
            pool.map(
                lambda s: _extract_cells_from_chunks(project, s, chunks_by_source[s.id]),
                sources,
            )
        )

    # 3. Persist matrix & entries, then compute synthesis
    matrix = LiteratureMatrix(
        project_id=project.id,
        owner_id=project.owner_id,
        name=data.name.strip(),
        synthesis_notes={},
    )
    db.add(matrix)
    db.flush()

    pairs: list[tuple[LiteratureEntry, ProjectSource]] = []
    for src, cells in zip(sources, extracted_cells_list, strict=False):
        entry = LiteratureEntry(
            matrix_id=matrix.id,
            project_source_id=src.id,
            project_id=project.id,
            owner_id=project.owner_id,
            cells=cells,
        )
        db.add(entry)
        pairs.append((entry, src))

    matrix.synthesis_notes = _build_synthesis(project, pairs)
    db.commit()
    db.refresh(matrix)
    return _to_matrix_detail(db, project, matrix)


def regenerate_matrix(
    db: Session, project: Project, matrix: LiteratureMatrix
) -> MatrixDetailOut:
    """Re-extract all cells and synthesis for an existing matrix without hitting project quota."""
    rows = db.execute(
        select(LiteratureEntry, ProjectSource)
        .join(ProjectSource, LiteratureEntry.project_source_id == ProjectSource.id)
        .where(LiteratureEntry.matrix_id == matrix.id)
        .order_by(LiteratureEntry.created_at.asc())
    ).all()
    if not rows:
        return _to_matrix_detail(db, project, matrix)

    sources = [src for _, src in rows]
    chunks_by_source: dict[uuid.UUID, list[DocumentChunk]] = {}
    for src in sources:
        chunks_by_source[src.id] = list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.project_source_id == src.id)
                .order_by(DocumentChunk.chunk_index)
            ).all()
        )

    with ThreadPoolExecutor(max_workers=min(5, len(sources))) as pool:
        extracted_cells_list = list(
            pool.map(
                lambda s: _extract_cells_from_chunks(project, s, chunks_by_source[s.id]),
                sources,
            )
        )

    pairs: list[tuple[LiteratureEntry, ProjectSource]] = []
    for (entry, src), cells in zip(rows, extracted_cells_list, strict=False):
        entry.cells = cells
        pairs.append((entry, src))

    matrix.synthesis_notes = _build_synthesis(project, pairs)
    db.commit()
    db.refresh(matrix)
    return _to_matrix_detail(db, project, matrix)


def update_entry_cell(
    db: Session,
    project: Project,
    matrix: LiteratureMatrix,
    entry_id: uuid.UUID,
    req: MatrixCellUpdateRequest,
) -> MatrixDetailOut:
    entry = db.scalar(
        select(LiteratureEntry).where(
            LiteratureEntry.id == entry_id,
            LiteratureEntry.matrix_id == matrix.id,
            LiteratureEntry.owner_id == project.owner_id,
        )
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matrix row not found")

    updated_cells = dict(entry.cells or {})
    updated_cells[req.field] = {
        "value": req.value.strip() or "Not reported",
        "page_number": None,
        "quote": None,
        "user_edited": True,
    }
    entry.cells = updated_cells
    db.commit()
    db.refresh(matrix)
    return _to_matrix_detail(db, project, matrix)


def delete_matrix(db: Session, matrix: LiteratureMatrix) -> None:
    db.delete(matrix)
    db.commit()


def export_matrix_csv(db: Session, project: Project, matrix: LiteratureMatrix) -> str:
    detail = _to_matrix_detail(db, project, matrix)
    buf = io.StringIO()
    writer = csv.writer(buf)
    columns = [
        ("author_year", "Author & Year"),
        ("title", "Study Title"),
        ("aim", "Research Aim"),
        ("methodology", "Methodology"),
        ("sample", "Population / Sample"),
        ("data_collection", "Data Collection"),
        ("analysis", "Analysis Method"),
        ("findings", "Key Findings"),
        ("limitations", "Limitations"),
        ("relevance", "Relevance"),
    ]
    writer.writerow([label for _, label in columns])
    for row in detail.entries:
        writer.writerow(
            [
                row.author_year,
                row.title,
                *[
                    (row.cells.get(col_key).value if col_key in row.cells else "Not reported")
                    for col_key, _ in columns[2:]
                ],
            ]
        )
    return buf.getvalue()


def export_matrix_docx(db: Session, project: Project, matrix: LiteratureMatrix) -> bytes:
    """Export the Literature Matrix and Cross-Study Synthesis as a formatted Word (.docx) file."""
    detail = _to_matrix_detail(db, project, matrix)
    word_doc = DocxDocument()

    word_doc.add_heading(detail.name, level=0)
    subtitle = word_doc.add_paragraph(f"Project: {project.name} — {project.topic}")
    subtitle.style = "Subtitle"

    columns = [
        ("study", "Study"),
        ("aim", "Research Aim"),
        ("methodology", "Methodology"),
        ("sample", "Population / Sample"),
        ("data_collection", "Data Collection"),
        ("analysis", "Analysis Method"),
        ("findings", "Key Findings"),
        ("limitations", "Limitations"),
        ("relevance", "Relevance"),
    ]

    word_doc.add_heading("Comparative Literature Matrix", level=1)
    table = word_doc.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for idx, (_, col_label) in enumerate(columns):
        hdr_cells[idx].text = col_label

    for row in detail.entries:
        row_cells = table.add_row().cells
        row_cells[0].text = f"{row.author_year}\n{row.title}"
        for col_idx, (col_key, _) in enumerate(columns[1:], start=1):
            cell = row.cells.get(col_key)
            if not cell:
                row_cells[col_idx].text = "Not reported"
            else:
                page_suffix = f" [p. {cell.page_number}]" if cell.page_number is not None else ""
                row_cells[col_idx].text = f"{cell.value}{page_suffix}"

    notes = detail.synthesis_notes
    word_doc.add_heading("Cross-Study Synthesis", level=1)

    if notes.themes:
        word_doc.add_heading("Recurring Themes & Findings", level=2)
        for t in notes.themes:
            srcs_str = f" ({', '.join(t.sources)})" if t.sources else ""
            word_doc.add_paragraph(f"{t.theme}{srcs_str}: {t.summary}", style="List Bullet")

    if notes.methodological_comparison:
        word_doc.add_heading("Methodological Comparison", level=2)
        word_doc.add_paragraph(notes.methodological_comparison)

    if notes.potential_gaps:
        word_doc.add_heading("Potential Research Gaps (Verify Against Literature)", level=2)
        for gap in notes.potential_gaps:
            word_doc.add_paragraph(gap, style="List Bullet")

    buf = io.BytesIO()
    word_doc.save(buf)
    return buf.getvalue()
