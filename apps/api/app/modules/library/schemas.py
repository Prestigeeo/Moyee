import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.discovery.schemas import AuthorItem, DiscoveredWork


class SaveDiscoveredSourceRequest(DiscoveredWork):
    notes: str | None = Field(default=None, max_length=5000)
    auto_import_pdf: bool = True


class ImportRemotePdfRequest(BaseModel):
    pdf_url: str | None = Field(default=None, max_length=1000)


class ManualSourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    authors: list[AuthorItem] = Field(default_factory=list)
    abstract: str | None = Field(default=None, max_length=20000)
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    venue: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=300)
    publication_type: str = Field(default="article", max_length=64)
    volume: str | None = Field(default=None, max_length=64)
    issue: str | None = Field(default=None, max_length=64)
    pages: str | None = Field(default=None, max_length=64)
    doi: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    oa_pdf_url: str | None = Field(default=None, max_length=1000)
    is_open_access: bool = False
    notes: str | None = Field(default=None, max_length=5000)


class ProjectSourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=1000)
    authors: list[AuthorItem] | None = None
    abstract: str | None = Field(default=None, max_length=20000)
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    venue: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=300)
    publication_type: str | None = Field(default=None, max_length=64)
    volume: str | None = Field(default=None, max_length=64)
    issue: str | None = Field(default=None, max_length=64)
    pages: str | None = Field(default=None, max_length=64)
    doi: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=5000)


class DocumentMetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str
    file_size_bytes: int
    page_count: int
    status: str
    error_message: str | None
    created_at: datetime


class ProjectSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    academic_source_id: uuid.UUID | None
    source_kind: str
    provider: str
    title: str
    authors: list[AuthorItem]
    abstract: str | None
    publication_year: int | None
    venue: str | None
    publisher: str | None
    publication_type: str
    volume: str | None
    issue: str | None
    pages: str | None
    doi: str | None
    source_url: str | None
    oa_pdf_url: str | None
    is_open_access: bool
    citation_count: int | None
    citation_key: str
    notes: str | None
    inline_citation: str
    formatted_reference: str
    missing_fields: list[str]
    document: DocumentMetaOut | None = None
    created_at: datetime
    updated_at: datetime


class DocumentPageOut(BaseModel):
    page_number: int
    text_content: str
    char_count: int


class SummarySectionOut(BaseModel):
    text: str
    quote: str | None = None
    page_number: int | None = None
    chunk_id: str | None = None


class SourceSummaryOut(BaseModel):
    project_source_id: uuid.UUID
    sections: dict[str, SummarySectionOut]
    updated_at: datetime


class ReaderViewOut(BaseModel):
    source: ProjectSourceOut
    pages: list[DocumentPageOut]
    summary: SourceSummaryOut | None = None
