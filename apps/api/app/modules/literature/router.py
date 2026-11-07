import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.modules.literature import service
from app.modules.literature.schemas import (
    MatrixCellUpdateRequest,
    MatrixCreate,
    MatrixDetailOut,
    MatrixSummaryOut,
)
from app.modules.projects.service import get_owned_project

router = APIRouter(prefix="/projects/{project_id}/matrices", tags=["literature"])


@router.get("", response_model=list[MatrixSummaryOut])
def list_matrices(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    return service.list_matrices(db, project)


@router.post("", response_model=MatrixDetailOut, status_code=status.HTTP_201_CREATED)
def create_matrix(
    project_id: uuid.UUID,
    data: MatrixCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    return service.create_matrix(db, project, data)


@router.get("/{matrix_id}", response_model=MatrixDetailOut)
def get_matrix(
    project_id: uuid.UUID,
    matrix_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    matrix = service.get_owned_matrix(db, user.id, project_id, matrix_id)
    return service._to_matrix_detail(db, project, matrix)


@router.post("/{matrix_id}/regenerate", response_model=MatrixDetailOut)
def regenerate_matrix(
    project_id: uuid.UUID,
    matrix_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    matrix = service.get_owned_matrix(db, user.id, project_id, matrix_id)
    return service.regenerate_matrix(db, project, matrix)


@router.patch("/{matrix_id}/entries/{entry_id}", response_model=MatrixDetailOut)
def edit_matrix_cell(
    project_id: uuid.UUID,
    matrix_id: uuid.UUID,
    entry_id: uuid.UUID,
    data: MatrixCellUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    matrix = service.get_owned_matrix(db, user.id, project_id, matrix_id)
    return service.update_entry_cell(db, project, matrix, entry_id, data)


@router.delete("/{matrix_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_matrix(
    project_id: uuid.UUID,
    matrix_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, user.id, project_id)
    matrix = service.get_owned_matrix(db, user.id, project_id, matrix_id)
    service.delete_matrix(db, matrix)


@router.get("/{matrix_id}/csv", response_class=PlainTextResponse)
def export_matrix_csv(
    project_id: uuid.UUID,
    matrix_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    matrix = service.get_owned_matrix(db, user.id, project_id, matrix_id)
    csv_text = service.export_matrix_csv(db, project, matrix)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{matrix.id}-matrix.csv"'},
    )


@router.get("/{matrix_id}/docx")
def export_matrix_docx(
    project_id: uuid.UUID,
    matrix_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user.id, project_id)
    matrix = service.get_owned_matrix(db, user.id, project_id, matrix_id)
    docx_bytes = service.export_matrix_docx(db, project, matrix)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{matrix.id}-matrix.docx"'},
    )
