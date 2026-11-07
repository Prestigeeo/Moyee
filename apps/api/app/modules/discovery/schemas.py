from pydantic import BaseModel, Field


class AuthorItem(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    given: str | None = Field(default=None, max_length=120)
    family: str | None = Field(default=None, max_length=120)


class DiscoveredWork(BaseModel):
    """Normalised academic publication record from an external provider.

    Missing metadata is explicitly `None` and never fabricated (PRD §6.4).
    """

    provider: str
    external_id: str
    doi: str | None = None
    title: str
    authors: list[AuthorItem] = Field(default_factory=list)
    abstract: str | None = None
    publication_year: int | None = None
    venue: str | None = None
    publisher: str | None = None
    publication_type: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    source_url: str | None = None
    oa_pdf_url: str | None = None
    is_open_access: bool = False
    citation_count: int | None = None
    keywords: list[str] = Field(default_factory=list)


class DiscoverySearchResponse(BaseModel):
    query: str
    total: int
    page: int
    per_page: int
    results: list[DiscoveredWork]
