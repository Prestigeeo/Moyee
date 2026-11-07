"""Project-scoped hybrid retrieval (Lexical + Semantic RRF) & prompt-injection sanitisation."""

import math
import re
import uuid
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.library.models import DocumentChunk, ProjectSource
from app.modules.projects.models import Project
from app.modules.references.formatter import format_inline_citation

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "what",
    "how",
    "why",
    "when",
    "where",
    "which",
    "does",
    "did",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "into",
    "about",
    "their",
    "there",
    "been",
}

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior)\s+directives", re.IGNORECASE),
]

CROSS_PAPER_REGEX = re.compile(
    r"\b(common\s+trends?|trends?|themes?|compare|comparison|synthesi[sz]e|"
    r"similarities|differences|these\s+papers|these\s+studies|all\s+papers|all\s+sources)\b",
    re.IGNORECASE,
)


def sanitize_chunk_text(text: str) -> str:
    """Neutralise embedded prompt-injection directives inside uploaded document chunks."""
    cleaned = text
    for pat in INJECTION_PATTERNS:
        cleaned = pat.sub("[redacted instruction]", cleaned)
    return cleaned


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", text) if w.lower() not in STOPWORDS]


def _stem_ngrams(tokens: list[str]) -> Counter[str]:
    """Generate morphological prefixes and character 4-grams for semantic/subword similarity."""
    grams: Counter[str] = Counter()
    for tok in tokens:
        grams[tok[:5]] += 2
        if len(tok) >= 4:
            for i in range(len(tok) - 3):
                grams[tok[i : i + 4]] += 1
    return grams


def _cosine_similarity(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    dot = sum(a[k] * b[k] for k in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_project_passages(
    db: Session,
    project: Project,
    query: str,
    *,
    source_ids: list[uuid.UUID] | None = None,
    top_k: int = 6,
) -> list[dict]:
    """Retrieve and rank chunks strictly belonging to `project` using Hybrid RRF."""
    stmt = (
        select(DocumentChunk, ProjectSource)
        .join(ProjectSource, DocumentChunk.project_source_id == ProjectSource.id)
        .where(
            DocumentChunk.project_id == project.id,
            DocumentChunk.owner_id == project.owner_id,
        )
    )
    if source_ids:
        stmt = stmt.where(DocumentChunk.project_source_id.in_(source_ids))

    rows = db.execute(stmt).all()
    if not rows:
        return []

    is_cross_paper = bool(CROSS_PAPER_REGEX.search(query))
    effective_query = f"{query} {project.topic or ''}" if is_cross_paper else query
    query_tokens = tokenize(effective_query)
    query_terms = set(query_tokens)
    query_grams = _stem_ngrams(query_tokens)

    lexical_scores: list[tuple[float, int]] = []
    semantic_scores: list[tuple[float, int]] = []

    for idx, (chunk, source) in enumerate(rows):
        chunk_tokens = tokenize(chunk.text_content)
        if not chunk_tokens:
            continue
        token_set = set(chunk_tokens)
        overlap = len(query_terms & token_set)
        exact_matches = sum(1 for t in query_terms if t in chunk.text_content.lower())
        title_matches = sum(1 for t in query_terms if t in (source.title or "").lower())
        lex_score = overlap * 2.0 + exact_matches * 1.0 + title_matches * 0.5

        chunk_grams = _stem_ngrams(chunk_tokens + tokenize(source.title or ""))
        sem_score = _cosine_similarity(query_grams, chunk_grams)

        if lex_score > 0 or sem_score >= 0.18 or is_cross_paper:
            lexical_scores.append((lex_score, idx))
            semantic_scores.append((sem_score, idx))

    if not lexical_scores:
        return []

    lexical_ranked = sorted(lexical_scores, key=lambda x: x[0], reverse=True)
    semantic_ranked = sorted(semantic_scores, key=lambda x: x[0], reverse=True)

    lex_rank_map = {row_idx: rank for rank, (_, row_idx) in enumerate(lexical_ranked, start=1)}
    sem_rank_map = {row_idx: rank for rank, (_, row_idx) in enumerate(semantic_ranked, start=1)}
    lex_score_map = {row_idx: score for score, row_idx in lexical_scores}

    rrf_k = 60.0
    fused: list[tuple[float, DocumentChunk, ProjectSource]] = []
    for row_idx in lex_rank_map:
        rrf_score = (1.0 / (rrf_k + lex_rank_map[row_idx])) + (
            0.8 / (rrf_k + sem_rank_map.get(row_idx, len(rows) + 1))
        )
        # Preserve lexical tie-breaking scale
        combined = round(rrf_score * 100.0 + lex_score_map[row_idx], 4)
        chunk, source = rows[row_idx]
        fused.append((combined, chunk, source))

    fused.sort(key=lambda item: item[0], reverse=True)

    # For cross-paper synthesis queries, ensure at least 1 top passage per distinct source first
    if is_cross_paper:
        seen_sources: set[uuid.UUID] = set()
        diverse: list[tuple[float, DocumentChunk, ProjectSource]] = []
        remainder: list[tuple[float, DocumentChunk, ProjectSource]] = []
        for item in fused:
            src_id = item[2].id
            if src_id not in seen_sources and len(diverse) < top_k:
                seen_sources.add(src_id)
                diverse.append(item)
            else:
                remainder.append(item)
        selected = (diverse + remainder)[:top_k]
    else:
        selected = fused[:top_k]

    passages: list[dict] = []
    for idx, (score, chunk, source) in enumerate(selected, start=1):
        passages.append(
            {
                "marker_id": f"S{idx}",
                "score": score,
                "chunk_id": chunk.id,
                "project_source_id": source.id,
                "source_title": source.title,
                "inline_label": format_inline_citation(source, project.citation_style, idx),
                "page_number": chunk.page_number,
                "text_content": sanitize_chunk_text(chunk.text_content),
            }
        )
    return passages
