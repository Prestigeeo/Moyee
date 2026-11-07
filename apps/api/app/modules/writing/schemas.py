import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WritingActionType = Literal["clarity", "grammar", "academic_tone", "shorten"]


class DocumentSectionItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(default="", max_length=100_000)


class ResearchDocumentCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)


class ResearchDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    sections: list[DocumentSectionItem] | None = None
    cited_source_ids: list[uuid.UUID] | None = None


class ResearchDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    sections: list[DocumentSectionItem]
    cited_source_ids: list[uuid.UUID]
    bibliography: list[str]
    word_count: int
    created_at: datetime
    updated_at: datetime


class WritingAssistRequest(BaseModel):
    action: WritingActionType
    text: str = Field(min_length=5, max_length=6000)


class WritingAssistOut(BaseModel):
    action: WritingActionType
    original: str
    suggestion: str
    note: str


class WritingAppendRequest(BaseModel):
    section_id: str | None = Field(default=None, max_length=64)
    new_section_title: str | None = Field(default=None, max_length=255)
    heading: str | None = Field(default=None, max_length=255)
    content: str = Field(min_length=1, max_length=50_000)
    cited_source_ids: list[uuid.UUID] = Field(default_factory=list)
