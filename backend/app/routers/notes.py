"""Notes API endpoints for manual meeting notes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import ManualNote, Meeting
from app.schemas.note import (
    NoteCreate,
    NoteListResponse,
    NotePositionUpdate,
    NoteResponse,
    NoteUpdate,
    NoteVisibilityUpdate,
)


router = APIRouter(tags=["notes"])


async def get_meeting_or_raise(db: AsyncSession, meeting_id: int) -> Meeting:
    """Get meeting by ID or raise 404."""
    result = await db.execute(
        select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.deleted_at.is_(None),
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with id {meeting_id} not found",
        )
    return meeting


async def get_note_or_raise(db: AsyncSession, note_id: int) -> ManualNote:
    """Get note by ID or raise 404."""
    result = await db.execute(
        select(ManualNote).where(ManualNote.id == note_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {note_id} not found",
        )
    return note


# ============================================
# Meeting Notes Endpoints
# ============================================


@router.get("/meetings/{meeting_id}/notes", response_model=NoteListResponse)
async def list_notes(
    meeting_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all notes for a meeting."""
    await get_meeting_or_raise(db, meeting_id)

    result = await db.execute(
        select(ManualNote)
        .where(ManualNote.meeting_id == meeting_id)
        .order_by(ManualNote.timestamp_seconds.asc().nullslast(), ManualNote.created_at)
    )
    notes = result.scalars().all()

    return NoteListResponse(
        data=[NoteResponse.model_validate(note) for note in notes],
        meta={"total": len(notes)},
    )


@router.post(
    "/meetings/{meeting_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    meeting_id: int,
    data: NoteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new note for a meeting."""
    await get_meeting_or_raise(db, meeting_id)

    note = ManualNote(
        meeting_id=meeting_id,
        content=data.content,
        agenda_id=data.agenda_id,
        timestamp_seconds=data.timestamp_seconds,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return NoteResponse.model_validate(note)


# ============================================
# Note Endpoints (by ID)
# ============================================


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a specific note by ID."""
    note = await get_note_or_raise(db, note_id)
    return NoteResponse.model_validate(note)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    data: NoteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a note."""
    note = await get_note_or_raise(db, note_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(note, key, value)

    await db.commit()
    await db.refresh(note)

    return NoteResponse.model_validate(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a note."""
    note = await get_note_or_raise(db, note_id)
    await db.delete(note)
    await db.commit()


# ============================================
# Interactive PostIt Endpoints
# ============================================


@router.patch("/notes/{note_id}/position", response_model=NoteResponse)
async def update_note_position(
    note_id: int,
    data: NotePositionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update note position (for draggable PostIt)."""
    note = await get_note_or_raise(db, note_id)

    note.position_x = data.position_x
    note.position_y = data.position_y
    if data.z_index is not None:
        note.z_index = data.z_index

    await db.commit()
    await db.refresh(note)
    return NoteResponse.model_validate(note)


@router.patch("/notes/{note_id}/visibility", response_model=NoteResponse)
async def update_note_visibility(
    note_id: int,
    data: NoteVisibilityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Toggle note visibility (hide/show PostIt)."""
    note = await get_note_or_raise(db, note_id)

    note.is_visible = data.is_visible

    await db.commit()
    await db.refresh(note)
    return NoteResponse.model_validate(note)
