"""Pydantic schemas for request/response validation."""

from app.schemas.contact import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactListResponse,
)
from app.schemas.meeting import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
    MeetingListResponse,
    MeetingDetailResponse,
    AttendeeCreate,
    AttendeeResponse,
)

__all__ = [
    # Contact schemas
    "ContactCreate",
    "ContactUpdate",
    "ContactResponse",
    "ContactListResponse",
    # Meeting schemas
    "MeetingCreate",
    "MeetingUpdate",
    "MeetingResponse",
    "MeetingListResponse",
    "MeetingDetailResponse",
    "AttendeeCreate",
    "AttendeeResponse",
]
