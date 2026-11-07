import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType, TimestampMixin


class LiteratureMatrix(TimestampMixin, Base):
    __tablename__ = "literature_matrices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    synthesis_notes: Mapped[dict] = mapped_column(JSONType, default=dict)


class LiteratureEntry(TimestampMixin, Base):
    __tablename__ = "literature_entries"
    __table_args__ = (UniqueConstraint("matrix_id", "project_source_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    matrix_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("literature_matrices.id", ondelete="CASCADE"), index=True
    )
    project_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_sources.id", ondelete="CASCADE")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    cells: Mapped[dict] = mapped_column(JSONType, default=dict)
