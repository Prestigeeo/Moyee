import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssistantMode = Literal["qa", "topic", "methodology", "explain"]


class ConversationCreate(BaseModel):
    title: str = Field(default="New Research Conversation", min_length=1, max_length=255)
    mode: AssistantMode = "qa"


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    mode: AssistantMode = "qa"
    source_ids: list[uuid.UUID] | None = None


class FeedbackRequest(BaseModel):
    feedback: Literal[-1, 1]


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    citation_number: int
    project_source_id: uuid.UUID
    chunk_id: uuid.UUID | None
    source_title: str
    inline_label: str
    page_number: int | None
    quote: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    interpretation: str | None
    limitations: str | None
    suggested_actions: list[str]
    insufficient_evidence: bool
    feedback: int | None
    provider: str | None
    model: str | None
    citations: list[CitationOut] = Field(default_factory=list)
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)
