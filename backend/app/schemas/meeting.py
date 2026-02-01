"""Pydantic schemas for Meeting API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MeetingStatus
from app.schemas.agenda import QuestionResponse, TimeSegment


class MeetingTypeResponse(BaseModel):
    """Schema for meeting type response."""

    id: int
    name: str
    description: Optional[str] = None
    question_perspective: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MeetingTypeCreate(BaseModel):
    """Schema for creating a meeting type."""

    name: str = Field(..., min_length=1, max_length=50, description="Meeting type name")
    description: Optional[str] = Field(None, description="Description of the meeting type")
    question_perspective: Optional[str] = Field(
        None, description="Perspective for generating discussion questions"
    )


class MeetingTypeUpdate(BaseModel):
    """Schema for updating a meeting type."""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Meeting type name")
    description: Optional[str] = Field(None, description="Description of the meeting type")
    question_perspective: Optional[str] = Field(
        None, description="Perspective for generating discussion questions"
    )


class AttendeeBase(BaseModel):
    """Base schema for meeting attendee."""

    contact_id: Optional[int] = Field(None, description="ID of the contact to add as attendee")
    name: Optional[str] = Field(None, max_length=100, description="Name for ad-hoc attendee (when no contact)")
    attended: bool = Field(default=False, description="Whether the contact attended")
    speaker_label: Optional[str] = Field(
        None,
        max_length=50,
        description="Speaker label for voice recognition"
    )


class AttendeeCreate(AttendeeBase):
    """Schema for adding an attendee to a meeting.

    Either contact_id or name must be provided.
    """
    pass


class AttendeeResponse(BaseModel):
    """Schema for attendee response."""

    id: int
    meeting_id: int
    contact_id: Optional[int] = None
    name: Optional[str] = None  # For ad-hoc attendees without contact
    attended: bool
    speaker_label: Optional[str] = None
    contact: Optional["ContactBrief"] = None

    model_config = ConfigDict(from_attributes=True)


class ContactBrief(BaseModel):
    """Brief contact info for attendee response."""

    id: int
    name: str
    organization: Optional[str] = None
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Update forward reference
AttendeeResponse.model_rebuild()


class AgendaBrief(BaseModel):
    """Brief agenda info for meeting response with hierarchical structure."""

    id: int
    order_num: int
    title: str
    description: Optional[str] = None
    status: str
    started_at_seconds: Optional[int] = None
    time_segments: Optional[list[TimeSegment]] = None
    parent_id: Optional[int] = None
    level: int = 0
    questions: list[QuestionResponse] = []
    children: list["AgendaBrief"] = []

    model_config = ConfigDict(from_attributes=True)


# Update forward reference for AgendaBrief self-reference
AgendaBrief.model_rebuild()


class MeetingBase(BaseModel):
    """Base schema for meeting data."""

    title: str = Field(..., min_length=1, max_length=200, description="Meeting title")
    type_id: Optional[int] = Field(None, description="Meeting type ID")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled date and time")
    location: Optional[str] = Field(None, max_length=200, description="Meeting location")


class MeetingCreate(MeetingBase):
    """Schema for creating a new meeting."""

    attendee_ids: Optional[list[int]] = Field(
        None,
        description="List of contact IDs to add as attendees"
    )


class MeetingUpdate(BaseModel):
    """Schema for updating a meeting (all fields optional)."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    type_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    status: Optional[MeetingStatus] = None


class MeetingResponse(BaseModel):
    """Schema for meeting response."""

    id: int
    title: str
    type_id: Optional[int] = None
    meeting_type: Optional[MeetingTypeResponse] = None
    scheduled_at: Optional[datetime] = None
    location: Optional[str] = None
    status: MeetingStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingDetailResponse(MeetingResponse):
    """Schema for detailed meeting response with attendees and agendas."""

    attendees: list[AttendeeResponse] = []
    agendas: list[AgendaBrief] = []


class MeetingListMeta(BaseModel):
    """Metadata for paginated meeting list."""

    total: int
    limit: int
    offset: int


class MeetingListResponse(BaseModel):
    """Schema for paginated meeting list response."""

    data: list[MeetingResponse]
    meta: MeetingListMeta
