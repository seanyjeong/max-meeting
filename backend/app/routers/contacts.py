"""Contacts API endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.schemas.contact import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactListResponse,
    ContactListMeta,
)
from app.services.contact import ContactService, contact_to_response_dict


router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Optional[str] = Query(
        None,
        description="Search query for contact name (uses pg_trgm)",
        max_length=100,
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of contacts"),
    offset: int = Query(0, ge=0, description="Number of contacts to skip"),
):
    """
    Get paginated list of contacts with optional search.

    - **q**: Search contacts by name (uses pg_trgm for fuzzy matching)
    - **limit**: Maximum number of contacts to return (1-100, default 20)
    - **offset**: Number of contacts to skip for pagination

    Phone numbers and emails are decrypted in the response.
    """
    service = ContactService(db)
    contacts, total = await service.get_list(q=q, limit=limit, offset=offset)

    return ContactListResponse(
        data=[
            ContactResponse(**contact_to_response_dict(contact))
            for contact in contacts
        ],
        meta=ContactListMeta(total=total, limit=limit, offset=offset),
    )


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a single contact by ID.

    Phone number and email are decrypted in the response.
    """
    service = ContactService(db)
    contact = await service.get_by_id(contact_id)

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    return ContactResponse(**contact_to_response_dict(contact))


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new contact.

    - **name**: Required contact name
    - **phone**: Phone number (will be encrypted at rest)
    - **email**: Email address (will be encrypted at rest)
    - **organization**: Organization/company name
    - **position/role**: Contact's role or position
    - **notes**: Additional notes
    """
    service = ContactService(db)
    contact = await service.create(data)

    return ContactResponse(**contact_to_response_dict(contact))


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing contact.

    Only provided fields are updated. Omit fields to leave them unchanged.
    """
    service = ContactService(db)
    contact = await service.get_by_id(contact_id)

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    updated_contact = await service.update(contact, data)

    return ContactResponse(**contact_to_response_dict(updated_contact))


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Soft delete a contact.

    The contact is not permanently removed but marked as deleted.
    Associated meeting attendee records are preserved.
    """
    service = ContactService(db)
    contact = await service.get_by_id(contact_id)

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    await service.delete(contact)

    return None
