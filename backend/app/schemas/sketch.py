"""Sketch-related Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ============================================
# Sketch Schemas
# ============================================


class SketchBase(BaseModel):
    """Base schema for sketches."""

    agenda_id: int | None = None
    timestamp_seconds: int | None = Field(default=None, ge=0)


class SketchCreate(SketchBase):
    """Schema for creating a sketch with image data."""

    image_data: str = Field(..., description="Base64 encoded PNG image data")


class SketchResponse(SketchBase):
    """Schema for sketch response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    thumbnail_path: str | None = None
    json_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class SketchListResponse(BaseModel):
    """Schema for sketch list response."""

    data: list[SketchResponse]
    meta: dict
