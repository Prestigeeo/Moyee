"""Research Writing Studio & DOCX export service (PRD §6.11, §6.14).

- Initialises documents from the project's template (Thesis, Journal Article, Report, Blank).
- Preserves configurable sections, inline citations, and auto-generated bibliography.
- Provides responsible AI writing actions (clarity, grammar, academic_tone, shorten) as a
  suggestion diff that never silently inserts fabricated facts or sources.
- Exports the structured document and bibliography to `.docx` via `python-docx`.
"""

import io
import re
import uuid

from docx import Document as DocxDocument
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.billing import service as billing
from app.modules.library.models import ProjectSource
from app.modules.projects.models import Project, ProjectTemplate
from app.modules.references.formatter import format_bibliography_entry
from app.modules.writing.models import ResearchDocument
from app.modules.writing.schemas import (
    DocumentSectionItem,
    ResearchDocumentCreate,
    ResearchDocumentOut,
    ResearchDocumentUpdate,
    WritingAppendRequest,
    WritingAssistOut,
    WritingAssistRequest,
)

TEMPLATE_SECTIONS: dict[ProjectTemplate, list[str]] = {
    ProjectTemplate.thesis: [
        "Abstract",
        "Chapter One: Introduction",
        "Chapter Two: Literature Review",
        "Chapter Three: Methodology",
        "Chapter Four: Results and Discussion",
        "Chapter Five: Summary, Conclusion and Recommendations",
    ],
    ProjectTemplate.journal_article: [
        "Abstract",
        "1. Introduction",
        "2. Related Work",
        "3. Methodology",
        "4. Results",
        "5. Discussion",
        "6. Conclusion",
    ],
    ProjectTemplate.report: [
        "Executive Summary",
        "Background & Objectives",
        "Methodology & Sources",
        "Key Findings",
        "Recommendations",
    ],
    ProjectTemplate.blank: [
        "Section 1",
    ],
}


def _default_sections(template: ProjectTemplate) -> list[dict]:
    titles = TEMPLATE_SECTIONS.get(template, TEMPLATE_SECTIONS[ProjectTemplate.blank])
    return [
        {"id": f"sec-{idx + 1}", "title": title, "content": ""} for idx, title in enumerate(titles)
    ]


def _build_bibliography(db: Session, project: Project, doc: ResearchDocument) -> list[str]:
    sources = list(
        db.scalars(
            select(ProjectSource)
            .where(
                ProjectSource.project_id == project.id,
                ProjectSource.owner_id == project.owner_id,
            )
            .order_by(ProjectSource.created_at.asc())
        ).all()
    )
    cited_ids = {str(sid) for sid in (doc.cited_source_ids or [])}
    full_text = "\n".join(s.get("content", "") for s in (doc.sections or []))

    included: list[ProjectSource] = []
    for src in sources:
        if str(src.id) in cited_ids or (src.title and src.title[:25].lower() in full_text.lower()):
            included.append(src)
        else:
            # Also include if the author's family name appears in the manuscript text
            first_fam = ((src.authors or [{}])[0].get("family") or "").lower()
            if first_fam and len(first_fam) >= 3 and first_fam in full_text.lower():
                included.append(src)

    target = included if included else sources
    return [
        format_bibliography_entry(src, project.citation_style, idx)
        for idx, src in enumerate(target, start=1)
    ]


def _to_doc_out(db: Session, project: Project, doc: ResearchDocument) -> ResearchDocumentOut:
    sections = [DocumentSectionItem(**s) for s in (doc.sections or [])]
    words = sum(len(s.content.split()) for s in sections)
    bib = _build_bibliography(db, project, doc)
    return ResearchDocumentOut(
        id=doc.id,
        project_id=doc.project_id,
        title=doc.title,
        sections=sections,
        cited_source_ids=[uuid.UUID(str(sid)) for sid in (doc.cited_source_ids or [])],
        bibliography=bib,
        word_count=words,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def get_or_create_primary_document(
    db: Session, project: Project, create_req: ResearchDocumentCreate | None = None
) -> ResearchDocumentOut:
    doc = db.scalar(
        select(ResearchDocument)
        .where(
            ResearchDocument.project_id == project.id,
            ResearchDocument.owner_id == project.owner_id,
        )
        .order_by(ResearchDocument.created_at.asc())
    )
    if doc is None:
        title = (create_req.title if create_req and create_req.title else project.name).strip()
        doc = ResearchDocument(
            project_id=project.id,
            owner_id=project.owner_id,
            title=title,
            sections=_default_sections(project.template),
            cited_source_ids=[],
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    return _to_doc_out(db, project, doc)


def get_owned_document(
    db: Session, owner_id: uuid.UUID, project_id: uuid.UUID, doc_id: uuid.UUID
) -> ResearchDocument:
    doc = db.scalar(
        select(ResearchDocument).where(
            ResearchDocument.id == doc_id,
            ResearchDocument.project_id == project_id,
            ResearchDocument.owner_id == owner_id,
        )
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research document not found"
        )
    return doc


def update_document(
    db: Session, project: Project, doc: ResearchDocument, data: ResearchDocumentUpdate
) -> ResearchDocumentOut:
    if data.title is not None:
        doc.title = data.title.strip()
    if data.sections is not None:
        doc.sections = [s.model_dump() for s in data.sections]
    if data.cited_source_ids is not None:
        doc.cited_source_ids = [str(sid) for sid in dict.fromkeys(data.cited_source_ids)]
    db.commit()
    db.refresh(doc)
    return _to_doc_out(db, project, doc)


def append_to_document(
    db: Session, project: Project, req: WritingAppendRequest
) -> ResearchDocumentOut:
    """Append an Assistant response or Literature Synthesis into a Writing Studio section."""
    get_or_create_primary_document(db, project)
    doc = db.scalar(
        select(ResearchDocument)
        .where(
            ResearchDocument.project_id == project.id,
            ResearchDocument.owner_id == project.owner_id,
        )
        .order_by(ResearchDocument.created_at.asc())
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research document not found"
        )

    sections = [dict(s) for s in (doc.sections or _default_sections(project.template))]
    block = req.content.strip()
    if req.heading and req.heading.strip():
        block = f"### {req.heading.strip()}\n\n{block}"

    if req.new_section_title and req.new_section_title.strip():
        new_id = f"sec-{len(sections) + 1}-{uuid.uuid4().hex[:6]}"
        sections.append(
            {
                "id": new_id,
                "title": req.new_section_title.strip(),
                "content": block,
            }
        )
    else:
        target_idx = 0
        if req.section_id:
            for idx, sec in enumerate(sections):
                if sec.get("id") == req.section_id:
                    target_idx = idx
                    break
        else:
            # Prefer Literature Review / Related Work section if available
            for idx, sec in enumerate(sections):
                t_low = (sec.get("title") or "").lower()
                if "literature" in t_low or "related work" in t_low or "findings" in t_low:
                    target_idx = idx
                    break
        existing = (sections[target_idx].get("content") or "").rstrip()
        sections[target_idx]["content"] = f"{existing}\n\n{block}".strip() if existing else block

    existing_cited = [str(sid) for sid in (doc.cited_source_ids or [])]
    for sid in req.cited_source_ids:
        sid_str = str(sid)
        if sid_str not in existing_cited:
            existing_cited.append(sid_str)

    doc.sections = sections
    doc.cited_source_ids = existing_cited
    db.commit()
    db.refresh(doc)
    return _to_doc_out(db, project, doc)


INFORMAL_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\ba lot of\b", "substantial"),
    (r"\blots of\b", "numerous"),
    (r"\bbig\b", "significant"),
    (r"\bget\b", "obtain"),
    (r"\bgot\b", "obtained"),
    (r"\bshow\b", "demonstrate"),
    (r"\bshows\b", "demonstrates"),
    (r"\blook at\b", "examine"),
    (r"\blooks at\b", "examines"),
    (r"\b find out\b", " determine"),
    (r"\bdon't\b", "do not"),
    (r"\bdoesn't\b", "does not"),
    (r"\bcan't\b", "cannot"),
    (r"\bwon't\b", "will not"),
    (r"\bit's\b", "it is"),
]

FILLER_PATTERNS: list[str] = [
    r"\bin order to\b",
    r"\bdue to the fact that\b",
    r"\bat this point in time\b",
    r"\b basically\b",
    r"\b actually\b",
    r"\b very\b",
    r"\b really\b",
]


def assist_writing_selection(
    db: Session, project: Project, req: WritingAssistRequest
) -> WritingAssistOut:
    """Apply a responsible writing transformation without adding unverified facts or citations."""
    billing.consume(db, project.owner_id, "writing_ai_actions")
    original = req.text.strip()
    revised = re.sub(r"[ \t]{2,}", " ", original)

    if req.action == "grammar":
        # Fix common contractions, double spaces, and sentence-initial capitalisation
        for pat, rep in INFORMAL_REPLACEMENTS[-5:]:
            revised = re.sub(pat, rep, revised, flags=re.IGNORECASE)
        sentences = re.split(r"(?<=[.!?])\s+", revised)
        revised = " ".join(s[0].upper() + s[1:] if s else s for s in sentences)
        if revised and revised[-1] not in ".!?":
            revised += "."
        note = "Standardised punctuation, capitalisation, and contractions without altering claims."

    elif req.action == "academic_tone":
        for pat, rep in INFORMAL_REPLACEMENTS:
            revised = re.sub(pat, rep, revised, flags=re.IGNORECASE)
        if revised and revised[0].islower():
            revised = revised[0].upper() + revised[1:]
        note = "Replaced informal phrasing with formal academic register. Verify meaning."

    elif req.action == "shorten":
        revised = re.sub(r"\bin order to\b", "to", revised, flags=re.IGNORECASE)
        revised = re.sub(r"\bdue to the fact that\b", "because", revised, flags=re.IGNORECASE)
        revised = re.sub(r"\bat this point in time\b", "currently", revised, flags=re.IGNORECASE)
        for pat in FILLER_PATTERNS[3:]:
            revised = re.sub(pat, "", revised, flags=re.IGNORECASE)
        revised = re.sub(r"[ \t]{2,}", " ", revised).strip()
        note = "Removed redundant filler phrases while keeping all cited statements intact."

    else:  # clarity
        for pat in FILLER_PATTERNS[3:]:
            revised = re.sub(pat, "", revised, flags=re.IGNORECASE)
        for pat, rep in INFORMAL_REPLACEMENTS[-5:]:
            revised = re.sub(pat, rep, revised, flags=re.IGNORECASE)
        revised = re.sub(r"[ \t]{2,}", " ", revised).strip()
        if revised and revised[0].islower():
            revised = revised[0].upper() + revised[1:]
        note = "Tightened phrasing for clarity. No new facts or citations were inserted."

    return WritingAssistOut(
        action=req.action,
        original=original,
        suggestion=revised,
        note=note,
    )


def export_docx_bytes(db: Session, project: Project, doc: ResearchDocument) -> bytes:
    """Build a `.docx` file preserving document title, section headings, content, and references."""
    out = _to_doc_out(db, project, doc)
    word_doc = DocxDocument()

    word_doc.add_heading(out.title, level=0)
    if project.topic:
        subtitle = word_doc.add_paragraph(project.topic)
        subtitle.style = "Subtitle"

    for sec in out.sections:
        word_doc.add_heading(sec.title, level=1)
        paragraphs = [p.strip() for p in sec.content.split("\n\n") if p.strip()]
        if not paragraphs:
            word_doc.add_paragraph("")
        else:
            for para in paragraphs:
                word_doc.add_paragraph(para)

    word_doc.add_heading("References", level=1)
    if not out.bibliography:
        word_doc.add_paragraph("No references cited yet.")
    else:
        for ref_line in out.bibliography:
            word_doc.add_paragraph(ref_line)

    buf = io.BytesIO()
    word_doc.save(buf)
    return buf.getvalue()
