import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.modules.library import service
from app.modules.library.models import Document
from app.modules.library.schemas import (
    ImportRemotePdfRequest,
    ManualSourceCreate,
    ProjectSourceOut,
    ProjectSourceUpdate,
    ReaderViewOut,
    SaveDiscoveredSourceRequest,
    SourceSummaryOut,
)
from app.modules.projects.service import get_owned_project
from app.modules.references.formatter import to_bibtex
from app.modules.users.models import CitationStyle

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["sources & references"])


@router.get("", response_model=list[ProjectSourceOut])
def list_sources(
    project_id: uuid.UUID,
    style: CitationStyle | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    effective_style = style or project.citation_style
    sources = service.list_project_sources(db, project)
    return [service.to_source_out(db, s, effective_style, i + 1) for i, s in enumerate(sources)]


@router.post(
    "/from-discovery", response_model=ProjectSourceOut, status_code=status.HTTP_201_CREATED
)
def save_from_discovery(
    project_id: uuid.UUID,
    data: SaveDiscoveredSourceRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    source = service.save_discovered_source(db, project, data)
    return service.to_source_out(db, source, project.citation_style, 1)


@router.post("/upload", response_model=ProjectSourceOut, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    raw_bytes = await file.read()
    source = service.upload_and_ingest_pdf(db, project, file.filename or "document.pdf", raw_bytes)
    return service.to_source_out(db, source, project.citation_style, 1)


@router.post("", response_model=ProjectSourceOut, status_code=status.HTTP_201_CREATED)
def create_manual(
    project_id: uuid.UUID,
    data: ManualSourceCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    source = service.create_manual_source(db, project, data)
    return service.to_source_out(db, source, project.citation_style, 1)


@router.get("/bibtex", response_class=PlainTextResponse)
def export_bibtex(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    sources = service.list_project_sources(db, project)
    return PlainTextResponse(
        content=to_bibtex(sources),
        media_type="application/x-bibtex; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{project.id}-references.bib"'},
    )


@router.get("/{source_id}/reader", response_model=ReaderViewOut)
def get_reader_view(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    source = service.get_owned_source(db, user.id, project_id, source_id)
    return service.get_reader_view(db, project, source)


@router.post("/{source_id}/summarize", response_model=SourceSummaryOut)
def summarize_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    source = service.get_owned_source(db, user.id, project_id, source_id)
    return service.summarize_source(db, project, source)


@router.post("/{source_id}/import-pdf", response_model=ProjectSourceOut)
def import_source_pdf(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    data: ImportRemotePdfRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    source = service.get_owned_source(db, user.id, project_id, source_id)
    updated = service.import_open_access_pdf(
        db,
        project,
        source,
        custom_pdf_url=data.pdf_url if data else None,
        raise_on_error=True,
    )
    return service.to_source_out(db, updated, project.citation_style, 1)


@router.get("/{source_id}/file")
def download_source_file(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, user.id, project_id)
    source = service.get_owned_source(db, user.id, project_id, source_id)
    doc = db.scalar(select(Document).where(Document.project_source_id == source.id))
    if doc is None or not Path(doc.storage_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original file not found")
    return FileResponse(
        path=doc.storage_path,
        media_type=doc.mime_type,
        filename=doc.filename,
    )


@router.patch("/{source_id}", response_model=ProjectSourceOut)
def update_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    data: ProjectSourceUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    source = service.get_owned_source(db, user.id, project_id, source_id)
    updated = service.update_project_source(db, source, data)
    return service.to_source_out(db, updated, project.citation_style, 1)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, user.id, project_id)
    source = service.get_owned_source(db, user.id, project_id, source_id)
    service.delete_project_source(db, source)
