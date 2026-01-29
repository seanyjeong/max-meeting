"""Pydantic schemas for Contact API."""

import re
from datetime import datetime
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def validate_email(v: str | None) -> str | None:
    """Validate email format using regex."""
    if v is None:
        return v
    # Basic email regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, v):
        raise ValueError("Invalid email format")
    return v.lower()


# Email type with validation
EmailType = Annotated[str | None, AfterValidator(validate_email)]


class ContactBase(BaseModel):
    """Base schema for contact data."""

    name: str = Field(..., min_length=1, max_length=100, description="Contact name")
    phone: str | None = Field(
        None,
        max_length=50,
        description="Phone number (will be encrypted)",
        examples=["010-1234-5678"]
    )
    email: EmailType = Field(
        None,
        description="Email address (will be encrypted)",
        examples=["contact@example.com"]
    )
    organization: str | None = Field(
        None,
        max_length=100,
        description="Organization/company name"
    )
    role: str | None = Field(
        None,
        max_length=50,
        description="Role/position",
        alias="position"
    )
    notes: str | None = Field(
        None,
        max_length=1000,
        description="Additional notes"
    )

    model_config = ConfigDict(
        populate_by_name=True,
    )


class ContactCreate(ContactBase):
    """Schema for creating a new contact."""
    pass


class ContactUpdate(BaseModel):
    """Schema for updating a contact (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: EmailType = None
    organization: str | None = Field(None, max_length=100)
    role: str | None = Field(None, max_length=50, alias="position")
    notes: str | None = Field(None, max_length=1000)

    model_config = ConfigDict(
        populate_by_name=True,
    )


class ContactResponse(BaseModel):
    """Schema for contact response."""

    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    position: Optional[str] = Field(None, alias="role")
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ContactListMeta(BaseModel):
    """Metadata for paginated contact list."""

    total: int
    limit: int
    offset: int


class ContactListResponse(BaseModel):
    """Schema for paginated contact list response."""

    data: list[ContactResponse]
    meta: ContactListMeta
