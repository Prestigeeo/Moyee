import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType, TimestampMixin
from app.modules.users.models import CitationStyle, ResearchLevel


class ProjectStatus(enum.StrEnum):
    active = "active"
    completed = "completed"
    archived = "archived"


class ProjectTemplate(enum.StrEnum):
    thesis = "thesis"
    journal_article = "journal_article"
    report = "report"
    blank = "blank"


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    topic: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    discipline: Mapped[str | None] = mapped_column(String(200))
    research_level: Mapped[ResearchLevel | None] = mapped_column(
        Enum(ResearchLevel, name="research_level", native_enum=False)
    )
    template: Mapped[ProjectTemplate] = mapped_column(
        Enum(ProjectTemplate, name="project_template", native_enum=False),
        default=ProjectTemplate.blank,
    )
    citation_style: Mapped[CitationStyle] = mapped_column(
        Enum(CitationStyle, name="citation_style", native_enum=False),
        default=CitationStyle.apa7,
    )
    objectives: Mapped[list] = mapped_column(JSONType, default=list)
    research_questions: Mapped[list] = mapped_column(JSONType, default=list)
    keywords: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status", native_enum=False),
        default=ProjectStatus.active,
        index=True,
    )
