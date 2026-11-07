import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.billing import service as billing
from app.modules.projects.models import Project, ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate


def _not_found() -> HTTPException:
    # 404 (not 403) so the existence of other users' projects is not revealed.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def get_owned_project(db: Session, owner_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    """The single gate for project access. Every project-scoped module must use it."""
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise _not_found()
    return project


def count_active(db: Session, owner_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Project)
            .where(Project.owner_id == owner_id, Project.status != ProjectStatus.archived)
        )
        or 0
    )


def list_projects(
    db: Session, owner_id: uuid.UUID, archived: bool = False, q: str | None = None
) -> list[Project]:
    stmt = select(Project).where(Project.owner_id == owner_id)
    if archived:
        stmt = stmt.where(Project.status == ProjectStatus.archived)
    else:
        stmt = stmt.where(Project.status != ProjectStatus.archived)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Project.name.ilike(like), Project.topic.ilike(like)))
    return list(db.scalars(stmt.order_by(Project.updated_at.desc())).all())


def create_project(db: Session, owner_id: uuid.UUID, data: ProjectCreate) -> Project:
    billing.ensure_capacity(db, owner_id, "active_projects", count_active(db, owner_id))
    project = Project(owner_id=owner_id, **data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    changes = data.model_dump(exclude_unset=True)
    restoring = project.status == ProjectStatus.archived and changes.get("status") not in (
        None,
        ProjectStatus.archived,
    )
    if restoring:
        billing.ensure_capacity(
            db, project.owner_id, "active_projects", count_active(db, project.owner_id)
        )
    for field, value in changes.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()
