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

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    ("aim", ["aim", "objective", "purpose", "this study", "examine", "investigate"]),
    (
        "methodology",
        [
            "methodology",
            "research design",
            "qualitative",
            "quantitative",
            "mixed",
            "panel",
            "experiment",
        ],
    ),
    (
        "sample",
        ["sample", "participants", "population", "respondents", "n =", "households", "students"],
    ),
    (
        "data_collection",
        ["survey", "questionnaire", "interview", "dataset", "records", "satellite", "observations"],
    ),
    (
        "analysis",
        ["regression", "anova", "correlation", "thematic", "statistical", "model", "estimated"],
    ),
    (
        "findings",
        [
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
        ["limitation", "constraint", "future research", "caveat", "shortcoming", "horizon"],
    ),
]


def _extract_cells_for_source(
    db: Session, project: Project, source: ProjectSource
) -> dict[str, dict]:
    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.project_source_id == source.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()

    cells: dict[str, dict] = {}
    for field_key, keywords in MATRIX_FIELD_KEYWORDS:
        best_score = 0
        best_sent: str | None = None
        best_page: int | None = None

        for chunk in chunks:
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", chunk.text_content.replace("\n", " "))
                if len(s.strip()) >= 25
            ]
            for sent in sentences:
                lower = sent.lower()
                score = sum(2 if kw in lower else 0 for kw in keywords)
                if score > best_score:
                    best_score = score
                    best_sent = sent
                    best_page = chunk.page_number

        if best_sent and best_score > 0:
            snippet = best_sent[:280]
            cells[field_key] = {
                "value": snippet,
                "page_number": best_page,
                "quote": snippet,
                "user_edited": False,
            }
        else:
            cells[field_key] = {
                "value": "Not reported",
                "page_number": None,
                "quote": None,
                "user_edited": False,
            }

    topic_terms = set(tokenize(project.topic))
    source_terms = set(tokenize(f"{source.title} {source.abstract or ''}"))
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
    term_sources: dict[str, list[str]] = {}
    methods_found: list[str] = []
    unreported_counts: Counter[str] = Counter()

    for idx, (entry, src) in enumerate(entries, start=1):
        label = format_inline_citation(src, project.citation_style, idx)
        tokens = set(tokenize(f"{src.title} {src.abstract or ''}"))
        for tok in tokens:
            if len(tok) >= 5:
                term_sources.setdefault(tok, [])
                if label not in term_sources[tok]:
                    term_sources[tok].append(label)

        method_val = (entry.cells.get("methodology") or {}).get("value", "Not reported")
        if method_val != "Not reported":
            methods_found.append(f"{label}: {method_val[:120]}")

        for key in ("sample", "limitations", "data_collection"):
            if (entry.cells.get(key) or {}).get("value") == "Not reported":
                unreported_counts[key] += 1

    ranked_terms = sorted(term_sources.items(), key=lambda kv: (len(kv[1]), kv[0]), reverse=True)[
        :4
    ]
    themes = [
        {
            "theme": term.capitalize(),
            "sources": srcs,
            "summary": f"Discussed across {len(srcs)} study(ies) ({', '.join(srcs)}).",
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

    matrix = LiteratureMatrix(
        project_id=project.id,
        owner_id=project.owner_id,
        name=data.name.strip(),
        synthesis_notes={},
    )
    db.add(matrix)
    db.flush()

    pairs: list[tuple[LiteratureEntry, ProjectSource]] = []
    for src in sources:
        cells = _extract_cells_for_source(db, project, src)
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
