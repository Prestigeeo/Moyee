import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MatrixFieldKey = Literal[
    "aim",
    "methodology",
    "sample",
    "data_collection",
    "analysis",
    "findings",
    "limitations",
    "relevance",
]


class MatrixCellOut(BaseModel):
    value: str
    page_number: int | None = None
    quote: str | None = None
    user_edited: bool = False


class MatrixCreate(BaseModel):
    name: str = Field(default="Comparative Literature Matrix", min_length=1, max_length=255)
    source_ids: list[uuid.UUID] = Field(min_length=1, max_length=15)


class MatrixAddSourcesRequest(BaseModel):
    source_ids: list[uuid.UUID] = Field(min_length=1, max_length=15)


class MatrixCellUpdateRequest(BaseModel):
    field: MatrixFieldKey
    value: str = Field(max_length=4000)


class MatrixEntryOut(BaseModel):
    id: uuid.UUID
    project_source_id: uuid.UUID
    author_year: str
    title: str
    cells: dict[str, MatrixCellOut]
    updated_at: datetime


class SynthesisThemeOut(BaseModel):
    theme: str
    sources: list[str]
    summary: str


class SynthesisNotesOut(BaseModel):
    themes: list[SynthesisThemeOut] = Field(default_factory=list)
    methodological_comparison: str = ""
    potential_gaps: list[str] = Field(default_factory=list)


class MatrixSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    entry_count: int = 0
    created_at: datetime
    updated_at: datetime


class MatrixDetailOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    entries: list[MatrixEntryOut]
    synthesis_notes: SynthesisNotesOut
    created_at: datetime
    updated_at: datetime
