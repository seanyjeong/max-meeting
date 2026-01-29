"""Pydantic schemas for Search API."""

from datetime import datetime

from pydantic import BaseModel, Field


class MeetingSearchResult(BaseModel):
    """Schema for meeting search result."""

    id: int
    title: str
    scheduled_at: datetime | None
    status: str
    highlight: str | None = Field(
        None,
        description="Highlighted match snippet from summary"
    )
    match_score: float = Field(
        description="Similarity score (0-1)"
    )

    class Config:
        from_attributes = True


class ContactSearchResult(BaseModel):
    """Schema for contact search result."""

    id: int
    name: str
    organization: str | None
    role: str | None
    highlight: str | None = Field(
        None,
        description="Highlighted match snippet from name"
    )
    match_score: float = Field(
        description="Similarity score (0-1)"
    )

    class Config:
        from_attributes = True


class TranscriptSearchResult(BaseModel):
    """Schema for transcript search result."""

    id: int
    meeting_id: int
    meeting_title: str
    chunk_index: int
    highlight: str | None = Field(
        None,
        description="Highlighted match snippet from transcript"
    )
    match_score: float = Field(
        description="Similarity score (0-1)"
    )
    created_at: datetime

    class Config:
        from_attributes = True


class SearchResults(BaseModel):
    """Schema for grouped search results."""

    meetings: list[MeetingSearchResult] = Field(
        default_factory=list,
        description="Matching meetings"
    )
    contacts: list[ContactSearchResult] = Field(
        default_factory=list,
        description="Matching contacts"
    )
    transcripts: list[TranscriptSearchResult] = Field(
        default_factory=list,
        description="Matching transcript chunks"
    )


class SearchMeta(BaseModel):
    """Metadata for search results."""

    query: str = Field(description="Search query")
    total: int = Field(description="Total results across all types")
    limit: int
    offset: int


class SearchResponse(BaseModel):
    """Schema for search API response."""

    data: SearchResults
    meta: SearchMeta
