"""Pydantic schemas for Meeting Type API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MeetingTypeCreate(BaseModel):
    """Schema for creating a new meeting type."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Meeting type name (e.g., 북부, 전국, 일산)"
    )
    description: Optional[str] = Field(
        None,
        description="Description of the meeting type"
    )
    question_perspective: Optional[str] = Field(
        None,
        description="Perspective for generating discussion questions"
    )


class MeetingTypeUpdate(BaseModel):
    """Schema for updating a meeting type."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Meeting type name"
    )
    description: Optional[str] = Field(
        None,
        description="Description of the meeting type"
    )
    question_perspective: Optional[str] = Field(
        None,
        description="Perspective for generating discussion questions"
    )


class MeetingTypeResponse(BaseModel):
    """Schema for meeting type response."""

    id: int
    name: str
    description: Optional[str] = None
    question_perspective: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MeetingTypeListResponse(BaseModel):
    """Schema for meeting type list response."""

    data: list[MeetingTypeResponse]
