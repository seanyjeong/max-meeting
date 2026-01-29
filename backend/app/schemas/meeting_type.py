"""Pydantic schemas for Meeting Type API."""

from pydantic import BaseModel, ConfigDict, Field


class MeetingTypeCreate(BaseModel):
    """Schema for creating a new meeting type."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Meeting type name (e.g., 북부, 전국, 일산)"
    )


class MeetingTypeResponse(BaseModel):
    """Schema for meeting type response."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class MeetingTypeListResponse(BaseModel):
    """Schema for meeting type list response."""

    data: list[MeetingTypeResponse]
