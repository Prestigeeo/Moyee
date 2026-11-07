import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.gateway import generate_project_recommendations
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db
from app.modules.library.models import ProjectSource
from app.modules.projects import service
from app.modules.projects.models import Project
from app.modules.projects.schemas import (
    ProjectCreate,
    ProjectOut,
    ProjectSuggestionOut,
    ProjectSuggestionRequest,
    ProjectUpdate,
)
from app.modules.users.service import get_or_create_profile

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(db: Session, project: Project) -> ProjectOut:
    count = (
        db.scalar(
            select(func.count())
            .select_from(ProjectSource)
            .where(ProjectSource.project_id == project.id)
        )
        or 0
    )
    out = ProjectOut.model_validate(project)
    out.source_count = count
    return out


@router.get("", response_model=list[ProjectOut])
def list_projects(
    archived: bool = False,
    q: str | None = Query(default=None, max_length=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [_out(db, p) for p in service.list_projects(db, user.id, archived=archived, q=q)]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_create_profile(db, user)
    return _out(db, service.create_project(db, user.id, data))


@router.post("/suggest", response_model=ProjectSuggestionOut)
def suggest_for_new_project(
    data: ProjectSuggestionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_create_profile(db, user)
    res = generate_project_recommendations(
        name=data.name,
        topic=data.topic,
        description=data.description,
        discipline=data.discipline,
        research_level=data.research_level.value if data.research_level else None,
        source_titles=[],
    )
    return ProjectSuggestionOut(**res)


@router.post("/{project_id}/suggest", response_model=ProjectSuggestionOut)
def suggest_for_existing_project(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = service.get_owned_project(db, user.id, project_id)
    source_titles = list(
        db.scalars(
            select(ProjectSource.title)
            .where(ProjectSource.project_id == project.id)
            .order_by(ProjectSource.created_at.desc())
            .limit(10)
        ).all()
    )
    res = generate_project_recommendations(
        name=project.name,
        topic=project.topic,
        description=project.description,
        discipline=project.discipline,
        research_level=project.research_level.value if project.research_level else None,
        source_titles=source_titles,
    )
    return ProjectSuggestionOut(**res)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _out(db, service.get_owned_project(db, user.id, project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = service.get_owned_project(db, user.id, project_id)
    return _out(db, service.update_project(db, project, data))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = service.get_owned_project(db, user.id, project_id)
    service.delete_project(db, project)
