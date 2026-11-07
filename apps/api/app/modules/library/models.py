import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType, TimestampMixin


class AcademicSource(TimestampMixin, Base):
    """Canonical record of an academic work discovered from an external provider."""

    __tablename__ = "academic_sources"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32))  # "openalex" | "crossref" | "manual"
    external_id: Mapped[str] = mapped_column(String(255))
    doi: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(Text)
    # List of {"given": str | None, "family": str | None, "name": str}
    authors: Mapped[list] = mapped_column(JSONType, default=list)
    abstract: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    venue: Mapped[str | None] = mapped_column(String(500))
    publisher: Mapped[str | None] = mapped_column(String(300))
    publication_type: Mapped[str | None] = mapped_column(String(64))
    volume: Mapped[str | None] = mapped_column(String(64))
    issue: Mapped[str | None] = mapped_column(String(64))
    pages: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    oa_pdf_url: Mapped[str | None] = mapped_column(String(1000))
    is_open_access: Mapped[bool] = mapped_column(Boolean, default=False)
    citation_count: Mapped[int | None] = mapped_column(Integer)
    keywords: Mapped[list] = mapped_column(JSONType, default=list)


class ProjectSource(TimestampMixin, Base):
    """A source saved to a specific research project, with editable reference metadata."""

    __tablename__ = "project_sources"
    __table_args__ = (UniqueConstraint("project_id", "academic_source_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    academic_source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("academic_sources.id", ondelete="SET NULL"), nullable=True
    )
    source_kind: Mapped[str] = mapped_column(String(32), default="metadata")
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[list] = mapped_column(JSONType, default=list)
    abstract: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    venue: Mapped[str | None] = mapped_column(String(500))
    publisher: Mapped[str | None] = mapped_column(String(300))
    publication_type: Mapped[str] = mapped_column(String(64), default="article")
    volume: Mapped[str | None] = mapped_column(String(64))
    issue: Mapped[str | None] = mapped_column(String(64))
    pages: Mapped[str | None] = mapped_column(String(64))
    doi: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    oa_pdf_url: Mapped[str | None] = mapped_column(String(1000))
    is_open_access: Mapped[bool] = mapped_column(Boolean, default=False)
    citation_count: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(32), default="manual")
    citation_key: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)


class Document(TimestampMixin, Base):
    """Uploaded research document (PDF/TXT) linked 1:1 with a ProjectSource."""

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("project_id", "sha256"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    project_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_sources.id", ondelete="CASCADE"), unique=True
    )
    filename: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str] = mapped_column(String(120), default="application/pdf")
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    # queued | processing | ready | failed
    status: Mapped[str] = mapped_column(String(32), default="queued")
    error_message: Mapped[str | None] = mapped_column(Text)


class DocumentPage(Base):
    """Extracted plain text per page of an uploaded document."""

    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    text_content: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0)


class DocumentChunk(TimestampMixin, Base):
    """Searchable passage chunk with page number and character offsets for evidence linking."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    project_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_sources.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    text_content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSONType, nullable=True)


class DocumentSummary(TimestampMixin, Base):
    """Structured, page-cited summary of a ProjectSource."""

    __tablename__ = "document_summaries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_sources.id", ondelete="CASCADE"), unique=True, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    sections: Mapped[dict] = mapped_column(JSONType, default=dict)
