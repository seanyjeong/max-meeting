"""Meetings API endpoints."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.enums import MeetingStatus
from app.schemas.meeting import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
    MeetingListResponse,
    MeetingDetailResponse,
    MeetingListMeta,
    AttendeeCreate,
    AttendeeResponse,
    ContactBrief,
    AgendaBrief,
)
from app.schemas.agenda import QuestionResponse
from app.schemas.segment_analysis import (
    AnalyzeSegmentsRequest,
    AnalyzeSegmentsResponse,
    MoveSegmentRequest,
    MoveSegmentResponse,
)
from app.services.meeting import MeetingService
from app.services.segment_analyzer import SegmentAnalyzer


router = APIRouter(prefix="/meetings", tags=["meetings"])


def _convert_agenda_to_brief(agenda) -> AgendaBrief:
    """Recursively convert an agenda model to AgendaBrief with children."""
    children = []
    if hasattr(agenda, 'children') and agenda.children:
        children = [_convert_agenda_to_brief(child) for child in agenda.children]

    return AgendaBrief(
        id=agenda.id,
        order_num=agenda.order_num,
        title=agenda.title,
        description=agenda.description,
        status=agenda.status,
        started_at_seconds=agenda.started_at_seconds,
        time_segments=agenda.time_segments,
        parent_id=agenda.parent_id,
        level=agenda.level,
        questions=[
            QuestionResponse(
                id=q.id,
                agenda_id=q.agenda_id,
                question=q.question,
                order_num=q.order_num,
                is_generated=q.is_generated,
                answered=q.answered,
            )
            for q in agenda.questions
        ],
        children=children,
    )


def _meeting_to_detail_response(meeting) -> MeetingDetailResponse:
    """Convert a meeting model to a detail response with nested data."""
    attendees = []
    for att in meeting.attendees:
        contact_brief = None
        if att.contact:
            contact_brief = ContactBrief(
                id=att.contact.id,
                name=att.contact.name,
                organization=att.contact.organization,
                role=att.contact.position,
            )
        attendees.append(AttendeeResponse(
            id=att.id,
            meeting_id=att.meeting_id,
            contact_id=att.contact_id,
            attended=att.attended,
            speaker_label=att.speaker_label,
            contact=contact_brief,
        ))

    # Build hierarchical agenda structure (only root-level items)
    agendas = [
        _convert_agenda_to_brief(agenda)
        for agenda in meeting.agendas
        if agenda.parent_id is None
    ]

    return MeetingDetailResponse(
        id=meeting.id,
        title=meeting.title,
        type_id=meeting.type_id,
        meeting_type=meeting.meeting_type,
        scheduled_at=meeting.scheduled_at,
        location=meeting.location,
        status=meeting.status,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        attendees=attendees,
        agendas=agendas,
    )


@router.get("", response_model=MeetingListResponse)
async def list_meetings(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[MeetingStatus] = Query(
        None,
        description="Filter by meeting status",
    ),
    type: Optional[int] = Query(
        None,
        description="Filter by meeting type ID",
        alias="type_id",
    ),
    from_date: Optional[datetime] = Query(
        None,
        description="Filter meetings scheduled on or after this date",
        alias="from",
    ),
    to_date: Optional[datetime] = Query(
        None,
        description="Filter meetings scheduled on or before this date",
        alias="to",
    ),
    deleted_only: bool = Query(
        False,
        description="Show only deleted meetings",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of meetings"),
    offset: int = Query(0, ge=0, description="Number of meetings to skip"),
):
    """
    Get paginated list of meetings with optional filters.

    - **status**: Filter by meeting status (draft, in_progress, completed)
    - **type_id**: Filter by meeting type
    - **from**: Filter meetings scheduled on or after this date
    - **to**: Filter meetings scheduled on or before this date
    - **deleted_only**: Show only deleted meetings (default: false)
    - **limit**: Maximum number of meetings to return (1-100, default 20)
    - **offset**: Number of meetings to skip for pagination
    """
    service = MeetingService(db)
    meetings, total = await service.get_list(
        status=status,
        type_id=type,
        from_date=from_date,
        to_date=to_date,
        deleted_only=deleted_only,
        limit=limit,
        offset=offset,
    )

    return MeetingListResponse(
        data=[MeetingResponse.model_validate(meeting) for meeting in meetings],
        meta=MeetingListMeta(total=total, limit=limit, offset=offset),
    )


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting(
    meeting_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a single meeting by ID with attendees and agendas.
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id, include_details=True)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    return _meeting_to_detail_response(meeting)


@router.post("", response_model=MeetingDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new meeting.

    - **title**: Required meeting title
    - **type_id**: Optional meeting type ID
    - **scheduled_at**: Optional scheduled date and time
    - **location**: Optional meeting location
    - **attendee_ids**: Optional list of contact IDs to add as attendees
    """
    service = MeetingService(db)
    meeting = await service.create(data)

    return _meeting_to_detail_response(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: int,
    data: MeetingUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing meeting.

    Only provided fields are updated. Omit fields to leave them unchanged.

    Status transitions are validated:
    - draft -> in_progress
    - in_progress -> completed
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    try:
        updated_meeting = await service.update(meeting, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MeetingResponse.model_validate(updated_meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Soft delete a meeting.

    The meeting is not permanently removed but marked as deleted.
    Associated agendas, recordings, and results are preserved.
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    await service.delete(meeting)

    return None


@router.post("/{meeting_id}/restore", response_model=MeetingResponse)
async def restore_meeting(
    meeting_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Restore a soft-deleted meeting.

    The meeting's deleted_at field is cleared, making it active again.
    """
    service = MeetingService(db)
    meeting = await service.restore(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제된 회의를 찾을 수 없습니다",
        )

    return MeetingResponse.model_validate(meeting)


@router.post(
    "/{meeting_id}/attendees",
    response_model=AttendeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_attendee(
    meeting_id: int,
    data: AttendeeCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add an attendee to a meeting.

    Either contact_id or name must be provided:
    - **contact_id**: ID of the contact to add as attendee
    - **name**: Name for ad-hoc attendee (when no contact)
    - **attended**: Whether the contact attended (default: false)
    - **speaker_label**: Label for voice recognition
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    try:
        attendee = await service.add_attendee(meeting_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    contact_brief = None
    if attendee.contact:
        contact_brief = ContactBrief(
            id=attendee.contact.id,
            name=attendee.contact.name,
            organization=attendee.contact.organization,
            role=attendee.contact.role,
        )

    return AttendeeResponse(
        id=attendee.id,
        meeting_id=attendee.meeting_id,
        contact_id=attendee.contact_id,
        name=attendee.name,
        attended=attendee.attended,
        speaker_label=attendee.speaker_label,
        contact=contact_brief,
    )


@router.delete(
    "/{meeting_id}/attendees/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_attendee(
    meeting_id: int,
    contact_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Remove an attendee from a meeting.
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    removed = await service.remove_attendee(meeting_id, contact_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendee not found",
        )

    return None


@router.delete(
    "/{meeting_id}/attendees/by-id/{attendee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_attendee_by_id(
    meeting_id: int,
    attendee_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Remove an attendee from a meeting by attendee ID.
    Use this for ad-hoc attendees without contact_id.
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    removed = await service.remove_attendee_by_id(meeting_id, attendee_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendee not found",
        )

    return None


# ============================================
# Transcript Endpoint
# ============================================


@router.get("/{meeting_id}/transcript")
async def get_meeting_transcript(
    meeting_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get combined transcript for a meeting (all recordings).
    Returns segments from all transcripts ordered by time.
    """
    from sqlalchemy import select
    from app.models.recording import Transcript

    # Check meeting exists
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    # Get all transcripts for this meeting
    result = await db.execute(
        select(Transcript)
        .where(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.recording_id, Transcript.chunk_index)
    )
    transcripts = result.scalars().all()

    if not transcripts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript found for this meeting",
        )

    # Combine all segments from all transcripts
    all_segments = []
    segment_id = 0
    for transcript in transcripts:
        if transcript.segments:
            for seg in transcript.segments:
                all_segments.append({
                    "id": segment_id,
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", ""),
                    "speaker_label": seg.get("speaker"),
                    "speaker_name": None,
                    "confidence": seg.get("confidence"),
                })
                segment_id += 1

    # Sort by start time
    all_segments.sort(key=lambda x: x["start"])

    return {
        "data": {
            "meeting_id": meeting_id,
            "segments": all_segments,
            "total_segments": len(all_segments),
        }
    }


# ============================================
# Segment Analysis Endpoints
# ============================================


@router.post("/{meeting_id}/analyze-segments", response_model=AnalyzeSegmentsResponse)
async def analyze_meeting_segments(
    meeting_id: int,
    request: AnalyzeSegmentsRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Analyze transcript segments for agenda mismatches using LLM.

    This endpoint analyzes each segment's content and compares it with
    the agenda it's currently matched to. If a mismatch is detected,
    it suggests a more appropriate agenda.
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id, include_details=True)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with id {meeting_id} not found",
        )

    analyzer = SegmentAnalyzer(db)
    result = await analyzer.analyze_segments(meeting, request.force_reanalyze)

    return AnalyzeSegmentsResponse(**result)


@router.patch("/{meeting_id}/segments/{segment_index}/move", response_model=MoveSegmentResponse)
async def move_segment(
    meeting_id: int,
    segment_index: int,
    request: MoveSegmentRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Move a segment to a different agenda.

    This updates the segment's matched_agenda_id and adds the segment's
    time range to the target agenda's time_segments.
    """
    service = MeetingService(db)
    meeting = await service.get_by_id(meeting_id, include_details=True)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with id {meeting_id} not found",
        )

    analyzer = SegmentAnalyzer(db)
    result = await analyzer.move_segment(
        meeting,
        segment_index,
        request.target_agenda_id,
        request.accept_suggestion,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to move segment"),
        )

    await db.commit()

    return MoveSegmentResponse(**result)
