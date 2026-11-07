import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.modules.projects.service import get_owned_project
from app.modules.writing import service
from app.modules.writing.schemas import (
    ResearchDocumentOut,
    ResearchDocumentUpdate,
    WritingAssistOut,
    WritingAssistRequest,
)

router = APIRouter(prefix="/projects/{project_id}/writing", tags=["writing & export"])


@router.get("", response_model=ResearchDocumentOut)
def get_primary_document(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    return service.get_or_create_primary_document(db, project)


@router.patch("/{document_id}", response_model=ResearchDocumentOut)
def update_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    data: ResearchDocumentUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    doc = service.get_owned_document(db, user.id, project_id, document_id)
    return service.update_document(db, project, doc, data)


@router.post("/assist", response_model=WritingAssistOut)
def assist_selection(
    project_id: uuid.UUID,
    data: WritingAssistRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    return service.assist_writing_selection(db, project, data)


@router.get("/{document_id}/docx")
def export_docx(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    doc = service.get_owned_document(db, user.id, project_id, document_id)
    docx_bytes = service.export_docx_bytes(db, project, doc)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{project.id}-manuscript.docx"'},
    )
