import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType, TimestampMixin


class ResearchDocument(TimestampMixin, Base):
    __tablename__ = "research_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    # List of {"id": str, "title": str, "content": str}
    sections: Mapped[list] = mapped_column(JSONType, default=list)
    # List of UUID strings of cited ProjectSources
    cited_source_ids: Mapped[list] = mapped_column(JSONType, default=list)
