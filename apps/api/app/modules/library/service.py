import hashlib
import logging
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.billing import service as billing
from app.modules.discovery.service import extract_doi, normalize_pdf_url
from app.modules.ingestion.service import (
    IngestionError,
    chunk_pages,
    extract_pdf_pages,
    generate_grounded_summary,
)
from app.modules.library.models import (
    AcademicSource,
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentSummary,
    ProjectSource,
)
from app.modules.library.schemas import (
    DocumentMetaOut,
    DocumentPageOut,
    ManualSourceCreate,
    ProjectSourceOut,
    ProjectSourceUpdate,
    ReaderViewOut,
    SaveDiscoveredSourceRequest,
    SourceSummaryOut,
)
from app.modules.projects.models import Project
from app.modules.references.formatter import (
    format_bibliography_entry,
    format_inline_citation,
    make_citation_key,
    missing_fields,
)
from app.modules.users.models import CitationStyle

logger = logging.getLogger("moyee.library")


def _index_abstract_chunk(db: Session, ps: ProjectSource) -> None:
    """Ensure metadata-only sources with an abstract have a searchable chunk."""
    db.query(DocumentChunk).filter(
        DocumentChunk.project_source_id == ps.id, DocumentChunk.document_id.is_(None)
    ).delete()
    if ps.abstract and ps.abstract.strip():
        text = ps.abstract.strip()
        db.add(
            DocumentChunk(
                project_id=ps.project_id,
                owner_id=ps.owner_id,
                project_source_id=ps.id,
                document_id=None,
                chunk_index=0,
                page_number=None,
                char_start=0,
                char_end=len(text),
                text_content=text,
            )
        )


def to_source_out(
    db: Session, source: ProjectSource, style: CitationStyle, index: int = 1
) -> ProjectSourceOut:
    doc = db.scalar(select(Document).where(Document.project_source_id == source.id))
    return ProjectSourceOut.model_validate(
        {
            **{col.name: getattr(source, col.name) for col in ProjectSource.__table__.columns},
            "inline_citation": format_inline_citation(source, style, index),
            "formatted_reference": format_bibliography_entry(source, style, index),
            "missing_fields": missing_fields(source),
            "document": DocumentMetaOut.model_validate(doc) if doc else None,
        }
    )


def list_project_sources(db: Session, project: Project) -> list[ProjectSource]:
    stmt = (
        select(ProjectSource)
        .where(ProjectSource.project_id == project.id, ProjectSource.owner_id == project.owner_id)
        .order_by(ProjectSource.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_owned_source(
    db: Session, owner_id: uuid.UUID, project_id: uuid.UUID, source_id: uuid.UUID
) -> ProjectSource:
    source = db.scalar(
        select(ProjectSource).where(
            ProjectSource.id == source_id,
            ProjectSource.project_id == project_id,
            ProjectSource.owner_id == owner_id,
        )
    )
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


def save_discovered_source(
    db: Session, project: Project, data: SaveDiscoveredSourceRequest
) -> ProjectSource:
    norm_doi = extract_doi(data.doi) if data.doi else None
    authors_dicts = [a.model_dump() for a in data.authors]

    academic = db.scalar(
        select(AcademicSource).where(
            AcademicSource.provider == data.provider,
            AcademicSource.external_id == data.external_id,
        )
    )
    if academic is None:
        academic = AcademicSource(
            provider=data.provider,
            external_id=data.external_id,
            doi=norm_doi,
            title=data.title.strip(),
            authors=authors_dicts,
            abstract=data.abstract,
            publication_year=data.publication_year,
            venue=data.venue,
            publisher=data.publisher,
            publication_type=data.publication_type or "article",
            volume=data.volume,
            issue=data.issue,
            pages=data.pages,
            source_url=data.source_url,
            oa_pdf_url=data.oa_pdf_url,
            is_open_access=data.is_open_access,
            citation_count=data.citation_count,
            keywords=data.keywords,
        )
        db.add(academic)
        db.flush()

    existing = db.scalar(
        select(ProjectSource).where(
            ProjectSource.project_id == project.id,
            ProjectSource.academic_source_id == academic.id,
        )
    )
    if existing is not None:
        if data.auto_import_pdf and existing.source_kind != "document" and existing.oa_pdf_url:
            import_open_access_pdf(db, project, existing, raise_on_error=False)
        return existing

    citation_key = make_citation_key(authors_dicts, data.publication_year, data.title)
    ps = ProjectSource(
        project_id=project.id,
        owner_id=project.owner_id,
        academic_source_id=academic.id,
        source_kind="metadata",
        provider=data.provider,
        title=data.title.strip(),
        authors=authors_dicts,
        abstract=data.abstract,
        publication_year=data.publication_year,
        venue=data.venue,
        publisher=data.publisher,
        publication_type=data.publication_type or "article",
        volume=data.volume,
        issue=data.issue,
        pages=data.pages,
        doi=norm_doi,
        source_url=data.source_url,
        oa_pdf_url=data.oa_pdf_url,
        is_open_access=data.is_open_access,
        citation_count=data.citation_count,
        citation_key=citation_key,
        notes=data.notes,
    )
    db.add(ps)
    db.flush()
    _index_abstract_chunk(db, ps)
    db.commit()
    db.refresh(ps)

    if data.auto_import_pdf and (ps.oa_pdf_url or ps.source_url):
        try:
            import_open_access_pdf(db, project, ps, raise_on_error=False)
        except Exception as exc:
            logger.warning("Auto PDF import skipped (%s)", type(exc).__name__)
            db.rollback()
            db.refresh(ps)
    return ps


def create_manual_source(db: Session, project: Project, data: ManualSourceCreate) -> ProjectSource:
    norm_doi = extract_doi(data.doi) if data.doi else None
    authors_dicts = [a.model_dump() for a in data.authors]
    citation_key = make_citation_key(authors_dicts, data.publication_year, data.title)
    ps = ProjectSource(
        project_id=project.id,
        owner_id=project.owner_id,
        academic_source_id=None,
        source_kind="manual",
        provider="manual",
        title=data.title.strip(),
        authors=authors_dicts,
        abstract=data.abstract,
        publication_year=data.publication_year,
        venue=data.venue,
        publisher=data.publisher,
        publication_type=data.publication_type or "article",
        volume=data.volume,
        issue=data.issue,
        pages=data.pages,
        doi=norm_doi,
        source_url=data.source_url,
        oa_pdf_url=data.oa_pdf_url,
        is_open_access=data.is_open_access,
        citation_key=citation_key,
        notes=data.notes,
    )
    db.add(ps)
    db.flush()
    _index_abstract_chunk(db, ps)
    db.commit()
    db.refresh(ps)
    return ps


def update_project_source(
    db: Session, source: ProjectSource, data: ProjectSourceUpdate
) -> ProjectSource:
    changes = data.model_dump(exclude_unset=True)
    if "authors" in changes and changes["authors"] is not None:
        changes["authors"] = [a.model_dump() for a in data.authors or []]
    if "doi" in changes and changes["doi"]:
        changes["doi"] = extract_doi(changes["doi"]) or changes["doi"]
    for field, value in changes.items():
        setattr(source, field, value)
    source.citation_key = make_citation_key(source.authors, source.publication_year, source.title)
    if "abstract" in changes:
        _index_abstract_chunk(db, source)
    db.commit()
    db.refresh(source)
    return source


def delete_project_source(db: Session, source: ProjectSource) -> None:
    doc = db.scalar(select(Document).where(Document.project_source_id == source.id))
    if doc and doc.storage_path:
        path = Path(doc.storage_path)
        if path.is_file():
            try:
                os.remove(path)
            except OSError:
                pass
    db.delete(source)
    db.commit()


def upload_and_ingest_pdf(
    db: Session, project: Project, filename: str, raw_bytes: bytes
) -> ProjectSource:
    """Validate, store, extract, chunk, and index an uploaded PDF document."""
    size_bytes = len(raw_bytes)
    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        )

    max_file_mb = billing.get_limit(db, project.owner_id, "max_file_mb") or 10
    if size_bytes > max_file_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds your plan's {max_file_mb} MB per-file limit.",
        )

    total_docs = (
        db.scalar(
            select(func.count()).select_from(Document).where(Document.owner_id == project.owner_id)
        )
        or 0
    )
    billing.ensure_capacity(db, project.owner_id, "documents", total_docs, 1)

    total_bytes = (
        db.scalar(
            select(func.coalesce(func.sum(Document.file_size_bytes), 0)).where(
                Document.owner_id == project.owner_id
            )
        )
        or 0
    )
    storage_limit_mb = billing.get_limit(db, project.owner_id, "storage_mb")
    if storage_limit_mb is not None and (total_bytes + size_bytes) > storage_limit_mb * 1024 * 1024:
        raise billing.QuotaExceeded("storage_mb", storage_limit_mb, None)

    if not raw_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only valid PDF files are supported.",
        )

    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    dup = db.scalar(
        select(Document).where(Document.project_id == project.id, Document.sha256 == sha256)
    )
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This PDF has already been uploaded to this project.",
        )

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename or "document.pdf").name)[:200]
    title_guess = (
        Path(filename or "Untitled Document").stem.replace("_", " ").replace("-", " ").strip()
    )
    title = title_guess or "Uploaded PDF"

    ps = ProjectSource(
        project_id=project.id,
        owner_id=project.owner_id,
        source_kind="document",
        provider="upload",
        title=title,
        authors=[],
        publication_type="article",
        citation_key=make_citation_key([], None, title),
    )
    db.add(ps)
    db.flush()

    storage_root = Path(get_settings().storage_dir) / str(project.owner_id) / str(project.id)
    storage_root.mkdir(parents=True, exist_ok=True)
    file_path = storage_root / f"{ps.id}_{safe_name}"
    file_path.write_bytes(raw_bytes)

    doc = Document(
        project_id=project.id,
        owner_id=project.owner_id,
        project_source_id=ps.id,
        filename=safe_name,
        mime_type="application/pdf",
        file_size_bytes=size_bytes,
        sha256=sha256,
        storage_path=str(file_path),
        status="processing",
    )
    db.add(doc)
    db.flush()

    try:
        extracted_pages = extract_pdf_pages(raw_bytes)
        doc.page_count = len(extracted_pages)
        for p in extracted_pages:
            db.add(
                DocumentPage(
                    document_id=doc.id,
                    project_id=project.id,
                    owner_id=project.owner_id,
                    page_number=p.page_number,
                    text_content=p.text,
                    char_count=len(p.text),
                )
            )
        for c in chunk_pages(extracted_pages):
            db.add(
                DocumentChunk(
                    project_id=project.id,
                    owner_id=project.owner_id,
                    project_source_id=ps.id,
                    document_id=doc.id,
                    chunk_index=c.chunk_index,
                    page_number=c.page_number,
                    char_start=c.char_start,
                    char_end=c.char_end,
                    text_content=c.text,
                )
            )
        if not ps.abstract and extracted_pages:
            ps.abstract = extracted_pages[0].text[:600]
        doc.status = "ready"
        doc.error_message = None
    except IngestionError as exc:
        doc.status = "failed"
        doc.error_message = str(exc)

    db.commit()
    db.refresh(ps)
    return ps


def _extract_pdf_bytes(raw: bytes) -> bytes | None:
    """Return PDF bytes starting from %PDF- header if present within first 1024 bytes."""
    idx = raw[:1024].find(b"%PDF-")
    if idx != -1:
        return raw[idx:]
    return None


def _fetch_pdf_bytes_from_url(url: str) -> bytes | None:
    """Download an open-access PDF, resolving landing-page citation_pdf_url tags when needed."""
    norm = normalize_pdf_url(url)
    if not norm:
        return None
    parsed = urlparse(norm)
    if not parsed.scheme or parsed.hostname in {"example.org", "example.com", "localhost"}:
        return None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 "
            "MoyeeResearch/0.1"
        ),
        "Accept": "application/pdf,application/octet-stream;q=0.9,text/html;q=0.8,*/*;q=0.7",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=18.0, headers=headers) as client:
            resp = client.get(norm)
            if resp.status_code >= 400:
                return None
            pdf_bytes = _extract_pdf_bytes(resp.content)
            if pdf_bytes is not None:
                return pdf_bytes

            # Check if response is an HTML landing page containing a citation_pdf_url meta tag
            ctype = (resp.headers.get("content-type") or "").lower()
            if "html" in ctype or b"<html" in resp.content[:2048].lower():
                html_head = resp.content[:120_000].decode("utf-8", errors="ignore")
                meta_match = re.search(
                    r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
                    html_head,
                    re.I,
                ) or re.search(
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
                    html_head,
                    re.I,
                )
                if meta_match:
                    pdf_href = urljoin(str(resp.url), meta_match.group(1).strip())
                    resp2 = client.get(normalize_pdf_url(pdf_href) or pdf_href)
                    if resp2.status_code < 400:
                        return _extract_pdf_bytes(resp2.content)
    except Exception as exc:
        logger.debug("Could not download open-access PDF from %s (%s)", norm, type(exc).__name__)
    return None


def import_open_access_pdf(
    db: Session,
    project: Project,
    ps: ProjectSource,
    custom_pdf_url: str | None = None,
    *,
    raise_on_error: bool = True,
) -> ProjectSource:
    """Fetch and ingest the full-text PDF for an existing `ProjectSource`."""
    candidate_urls: list[str] = []
    doi_url = f"https://doi.org/{ps.doi}" if ps.doi else None
    for u in (custom_pdf_url, ps.oa_pdf_url, ps.source_url, doi_url):
        if u and u.strip() and u.strip() not in candidate_urls:
            candidate_urls.append(u.strip())

    if not candidate_urls:
        if raise_on_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Open-Access PDF link or DOI is available for this source.",
            )
        return ps

    raw_bytes: bytes | None = None
    used_url: str | None = None
    for url in candidate_urls:
        raw_bytes = _fetch_pdf_bytes_from_url(url)
        if raw_bytes is not None:
            used_url = url
            break

    if raw_bytes is None:
        if raise_on_error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "The publisher blocked automated PDF downloading or only provides an HTML "
                    "landing page. Please open the Source Link in your browser, save the PDF, "
                    "and upload it to your Library."
                ),
            )
        return ps

    max_file_mb = billing.get_limit(db, project.owner_id, "max_file_mb") or 10
    if len(raw_bytes) > max_file_mb * 1024 * 1024:
        if raise_on_error:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Remote PDF exceeds your plan's {max_file_mb} MB per-file limit.",
            )
        return ps

    try:
        extracted_pages = extract_pdf_pages(raw_bytes)
    except IngestionError as exc:
        if raise_on_error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        return ps

    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", f"{ps.citation_key or 'paper'}.pdf")[:200]
    storage_root = Path(get_settings().storage_dir) / str(project.owner_id) / str(project.id)
    storage_root.mkdir(parents=True, exist_ok=True)
    file_path = storage_root / f"{ps.id}_{safe_name}"
    file_path.write_bytes(raw_bytes)

    existing_doc = db.scalar(select(Document).where(Document.project_source_id == ps.id))
    if existing_doc is not None:
        db.delete(existing_doc)
        db.flush()

    # Remove abstract-only chunks now that full-text pages are available
    db.query(DocumentChunk).filter(DocumentChunk.project_source_id == ps.id).delete()

    doc = Document(
        project_id=project.id,
        owner_id=project.owner_id,
        project_source_id=ps.id,
        filename=safe_name,
        mime_type="application/pdf",
        file_size_bytes=len(raw_bytes),
        sha256=sha256,
        storage_path=str(file_path),
        page_count=len(extracted_pages),
        status="ready",
    )
    db.add(doc)
    db.flush()

    for p in extracted_pages:
        db.add(
            DocumentPage(
                document_id=doc.id,
                project_id=project.id,
                owner_id=project.owner_id,
                page_number=p.page_number,
                text_content=p.text,
                char_count=len(p.text),
            )
        )
    for c in chunk_pages(extracted_pages):
        db.add(
            DocumentChunk(
                project_id=project.id,
                owner_id=project.owner_id,
                project_source_id=ps.id,
                document_id=doc.id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                char_start=c.char_start,
                char_end=c.char_end,
                text_content=c.text,
            )
        )

    ps.source_kind = "document"
    if used_url and not ps.oa_pdf_url:
        ps.oa_pdf_url = used_url
    if not ps.abstract and extracted_pages:
        ps.abstract = extracted_pages[0].text[:600]

    db.commit()
    db.refresh(ps)
    return ps


def get_reader_view(db: Session, project: Project, source: ProjectSource) -> ReaderViewOut:
    doc = db.scalar(select(Document).where(Document.project_source_id == source.id))
    pages: list[DocumentPageOut] = []
    if doc:
        rows = db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.page_number)
        ).all()
        pages = [
            DocumentPageOut(
                page_number=r.page_number, text_content=r.text_content, char_count=r.char_count
            )
            for r in rows
        ]
    if not pages and source.abstract:
        pages = [
            DocumentPageOut(
                page_number=1,
                text_content=source.abstract,
                char_count=len(source.abstract),
            )
        ]

    summary_row = db.scalar(
        select(DocumentSummary).where(DocumentSummary.project_source_id == source.id)
    )
    summary_out = (
        SourceSummaryOut(
            project_source_id=source.id,
            sections=summary_row.sections,
            updated_at=summary_row.updated_at,
        )
        if summary_row
        else None
    )
    return ReaderViewOut(
        source=to_source_out(db, source, project.citation_style, 1),
        pages=pages,
        summary=summary_out,
    )


def summarize_source(db: Session, project: Project, source: ProjectSource) -> SourceSummaryOut:
    """Generate or refresh a structured, page-cited summary for `source`."""
    billing.consume(db, project.owner_id, "document_summaries")
    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.project_source_id == source.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This source has no extractable text to summarise.",
        )

    chunk_dicts = [
        {"id": c.id, "page_number": c.page_number, "text_content": c.text_content} for c in chunks
    ]
    sections = generate_grounded_summary(chunk_dicts)

    summary_row = db.scalar(
        select(DocumentSummary).where(DocumentSummary.project_source_id == source.id)
    )
    if summary_row is None:
        summary_row = DocumentSummary(
            project_source_id=source.id,
            project_id=project.id,
            owner_id=project.owner_id,
            sections=sections,
        )
        db.add(summary_row)
    else:
        summary_row.sections = sections
    db.commit()
    db.refresh(summary_row)
    return SourceSummaryOut(
        project_source_id=source.id,
        sections=summary_row.sections,
        updated_at=summary_row.updated_at,
    )
