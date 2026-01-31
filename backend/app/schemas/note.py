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

    bg_color: str | None = Field(default=None, max_length=20)
    text_color: str | None = Field(default=None, max_length=20)


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
    position_x: float | None = None
    position_y: float | None = None
    rotation: float | None = None
    is_visible: bool = True
    z_index: int = 0
    bg_color: str | None = None
    text_color: str | None = None
    created_at: datetime
    updated_at: datetime


class NoteListResponse(BaseModel):
    """Schema for note list response."""

    data: list[NoteResponse]
    meta: dict


# ============================================
# Interactive PostIt Schemas
# ============================================


class NotePositionUpdate(BaseModel):
    """Schema for updating note position."""

    position_x: float = Field(..., ge=0, le=100, description="X coordinate (%)")
    position_y: float = Field(..., ge=0, le=100, description="Y coordinate (%)")
    z_index: int | None = Field(default=None, description="Layer order")


class NoteVisibilityUpdate(BaseModel):
    """Schema for toggling note visibility."""

    is_visible: bool
