"""Note-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================
# Note Schemas
# ============================================


class NoteBase(BaseModel):
    """Base schema for manual notes."""

    content: str = Field(..., min_length=1, max_length=50000)
    agenda_id: int | None = None
    timestamp_seconds: int | None = Field(default=None, ge=0)


class NoteCreate(NoteBase):
    """Schema for creating a note."""

    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note."""

    content: str | None = Field(default=None, min_length=1, max_length=50000)
    agenda_id: int | None = None
    timestamp_seconds: int | None = Field(default=None, ge=0)


class NoteResponse(NoteBase):
    """Schema for note response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    created_at: datetime
    updated_at: datetime


class NoteListResponse(BaseModel):
    """Schema for note list response."""

    data: list[NoteResponse]
    meta: dict
