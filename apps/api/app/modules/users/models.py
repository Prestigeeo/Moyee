import enum
import uuid

from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class ResearchLevel(enum.StrEnum):
    undergraduate = "undergraduate"
    postgraduate = "postgraduate"
    professional = "professional"


class CitationStyle(enum.StrEnum):
    apa7 = "apa7"
    harvard = "harvard"
    ieee = "ieee"


class Profile(TimestampMixin, Base):
    """Application profile. `id` equals the Supabase auth user id."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320))
    full_name: Mapped[str | None] = mapped_column(String(200))
    research_level: Mapped[ResearchLevel | None] = mapped_column(
        Enum(ResearchLevel, name="research_level", native_enum=False)
    )
    discipline: Mapped[str | None] = mapped_column(String(200))
    default_citation_style: Mapped[CitationStyle] = mapped_column(
        Enum(CitationStyle, name="citation_style", native_enum=False),
        default=CitationStyle.apa7,
    )
