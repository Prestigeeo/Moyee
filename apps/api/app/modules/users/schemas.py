import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.models import CitationStyle, ResearchLevel


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    full_name: str | None
    research_level: ResearchLevel | None
    discipline: str | None
    default_citation_style: CitationStyle
    created_at: datetime


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    research_level: ResearchLevel | None = None
    discipline: str | None = Field(default=None, max_length=200)
    default_citation_style: CitationStyle | None = None
