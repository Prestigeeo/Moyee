import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.projects.models import ProjectStatus, ProjectTemplate
from app.modules.users.models import CitationStyle, ResearchLevel


def _clean_list(values: list[str]) -> list[str]:
    seen: list[str] = []
    for v in values:
        v = v.strip()
        if v and v not in seen:
            seen.append(v[:500])
    return seen[:30]


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    discipline: str | None = Field(default=None, max_length=200)
    research_level: ResearchLevel | None = None
    template: ProjectTemplate = ProjectTemplate.blank
    citation_style: CitationStyle = CitationStyle.apa7
    objectives: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    _clean = field_validator("objectives", "research_questions", "keywords")(_clean_list)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    topic: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    discipline: str | None = Field(default=None, max_length=200)
    research_level: ResearchLevel | None = None
    template: ProjectTemplate | None = None
    citation_style: CitationStyle | None = None
    objectives: list[str] | None = None
    research_questions: list[str] | None = None
    keywords: list[str] | None = None
    status: ProjectStatus | None = None

    @field_validator("objectives", "research_questions", "keywords")
    @classmethod
    def _clean(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else _clean_list(v)


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ProjectStatus
    source_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectSuggestionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    discipline: str | None = Field(default=None, max_length=200)
    research_level: ResearchLevel | None = None


class ProjectSuggestionOut(BaseModel):
    refined_description: str
    research_questions: list[str]
    objectives: list[str]
    keywords: list[str]
    methodology_recommendation: str
    provider: str
    model: str
