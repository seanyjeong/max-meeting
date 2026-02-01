"""Meeting Types API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.meeting import MeetingType
from app.schemas.meeting_type import (
    MeetingTypeCreate,
    MeetingTypeUpdate,
    MeetingTypeResponse,
    MeetingTypeListResponse,
)


router = APIRouter(prefix="/meeting-types", tags=["meeting-types"])


@router.get("", response_model=MeetingTypeListResponse)
async def list_meeting_types(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get list of all meeting types.

    Returns all non-deleted meeting types ordered by name.
    """
    stmt = (
        select(MeetingType)
        .where(MeetingType.deleted_at.is_(None))
        .order_by(MeetingType.name)
    )
    result = await db.execute(stmt)
    meeting_types = result.scalars().all()

    return MeetingTypeListResponse(
        data=[MeetingTypeResponse.model_validate(mt) for mt in meeting_types]
    )


@router.post("", response_model=MeetingTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting_type(
    data: MeetingTypeCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new meeting type.

    - **name**: Required meeting type name (must be unique)
    """
    # Check if meeting type with same name already exists
    stmt = select(MeetingType).where(
        MeetingType.name == data.name,
        MeetingType.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Meeting type '{data.name}' already exists",
        )

    meeting_type = MeetingType(
        name=data.name,
        description=data.description,
        question_perspective=data.question_perspective,
    )
    db.add(meeting_type)
    await db.commit()
    await db.refresh(meeting_type)

    return MeetingTypeResponse.model_validate(meeting_type)


@router.patch("/{type_id}", response_model=MeetingTypeResponse)
async def update_meeting_type(
    type_id: int,
    data: MeetingTypeUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a meeting type.

    - **name**: Optional new name for the meeting type
    - **description**: Optional description
    - **question_perspective**: Optional perspective for question generation
    """
    stmt = select(MeetingType).where(
        MeetingType.id == type_id,
        MeetingType.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    meeting_type = result.scalar_one_or_none()

    if not meeting_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting type not found",
        )

    # Check for duplicate name if name is being changed
    if data.name is not None and data.name != meeting_type.name:
        stmt = select(MeetingType).where(
            MeetingType.name == data.name,
            MeetingType.deleted_at.is_(None),
            MeetingType.id != type_id,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Meeting type '{data.name}' already exists",
            )
        meeting_type.name = data.name

    # Use model_fields_set to distinguish between "not provided" and "explicitly set to null"
    if "description" in data.model_fields_set:
        meeting_type.description = data.description

    if "question_perspective" in data.model_fields_set:
        meeting_type.question_perspective = data.question_perspective

    await db.commit()
    await db.refresh(meeting_type)

    return MeetingTypeResponse.model_validate(meeting_type)


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting_type(
    type_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Soft delete a meeting type.

    The meeting type is not permanently removed but marked as deleted.
    Associated meetings are preserved with their type_id reference.
    """
    stmt = select(MeetingType).where(
        MeetingType.id == type_id,
        MeetingType.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    meeting_type = result.scalar_one_or_none()

    if not meeting_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting type not found",
        )

    from datetime import datetime, timezone
    meeting_type.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return None
