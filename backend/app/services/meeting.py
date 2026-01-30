"""Meeting service with CRUD operations."""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Meeting, MeetingAttendee, MeetingType
from app.models.agenda import Agenda
from app.models.enums import MeetingStatus
from app.schemas.meeting import MeetingCreate, MeetingUpdate, AttendeeCreate


class MeetingService:
    """Service for managing meetings."""

    def __init__(self, db: AsyncSession):
        """Initialize the meeting service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def get_list(
        self,
        status: Optional[MeetingStatus] = None,
        type_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        deleted_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Meeting], int]:
        """
        Get paginated list of meetings with optional filters.

        Args:
            status: Filter by meeting status.
            type_id: Filter by meeting type ID.
            from_date: Filter meetings scheduled on or after this date.
            to_date: Filter meetings scheduled on or before this date.
            deleted_only: If True, show only deleted meetings. Otherwise, show only active meetings.
            limit: Maximum number of meetings to return.
            offset: Number of meetings to skip.

        Returns:
            Tuple of (list of meetings, total count).
        """
        # Build base query with soft-delete filter and eager loading
        if deleted_only:
            base_query = (
                select(Meeting)
                .where(Meeting.deleted_at.isnot(None))
                .options(selectinload(Meeting.meeting_type))
            )
        else:
            base_query = (
                select(Meeting)
                .where(Meeting.deleted_at.is_(None))
                .options(selectinload(Meeting.meeting_type))
            )

        # Apply filters
        filters = []
        if status:
            filters.append(Meeting.status == status)
        if type_id:
            filters.append(Meeting.type_id == type_id)
        if from_date:
            filters.append(Meeting.scheduled_at >= from_date)
        if to_date:
            filters.append(Meeting.scheduled_at <= to_date)

        if filters:
            base_query = base_query.where(and_(*filters))

        # Get total count
        if deleted_only:
            count_subquery = (
                select(Meeting.id)
                .where(Meeting.deleted_at.isnot(None))
            )
        else:
            count_subquery = (
                select(Meeting.id)
                .where(Meeting.deleted_at.is_(None))
            )
        if filters:
            count_subquery = count_subquery.where(and_(*filters))
        count_query = select(func.count()).select_from(count_subquery.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = (
            base_query
            .order_by(Meeting.scheduled_at.desc().nulls_last(), Meeting.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        meetings = list(result.scalars().unique().all())

        return meetings, total

    async def get_by_id(
        self,
        meeting_id: int,
        include_details: bool = False,
    ) -> Optional[Meeting]:
        """
        Get a single meeting by ID.

        Args:
            meeting_id: The meeting's ID.
            include_details: If True, eager load attendees and agendas.

        Returns:
            The meeting if found and not deleted, None otherwise.
        """
        query = (
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .where(Meeting.deleted_at.is_(None))
            .options(selectinload(Meeting.meeting_type))
        )

        if include_details:
            query = query.options(
                selectinload(Meeting.attendees).selectinload(MeetingAttendee.contact),
                # Load agendas with questions
                selectinload(Meeting.agendas)
                    .selectinload(Agenda.questions),
                # Load 1st level children with questions
                selectinload(Meeting.agendas)
                    .selectinload(Agenda.children)
                    .selectinload(Agenda.questions),
                # Load 2nd level children (grandchildren) with questions
                selectinload(Meeting.agendas)
                    .selectinload(Agenda.children)
                    .selectinload(Agenda.children)
                    .selectinload(Agenda.questions),
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: MeetingCreate) -> Meeting:
        """
        Create a new meeting.

        Args:
            data: The meeting data.

        Returns:
            The created meeting.
        """
        # Create meeting
        meeting = Meeting(
            title=data.title,
            type_id=data.type_id,
            scheduled_at=data.scheduled_at,
            location=data.location,
            status=MeetingStatus.DRAFT,
        )

        self.db.add(meeting)
        await self.db.flush()

        # Add attendees if provided
        if data.attendee_ids:
            for contact_id in data.attendee_ids:
                attendee = MeetingAttendee(
                    meeting_id=meeting.id,
                    contact_id=contact_id,
                    attended=False,
                )
                self.db.add(attendee)

        await self.db.flush()
        await self.db.refresh(meeting)

        # Reload with relationships
        return await self.get_by_id(meeting.id, include_details=True)

    async def update(
        self,
        meeting: Meeting,
        data: MeetingUpdate,
    ) -> Meeting:
        """
        Update an existing meeting.

        Args:
            meeting: The meeting to update.
            data: The update data (only provided fields are updated).

        Returns:
            The updated meeting.
        """
        update_data = data.model_dump(exclude_unset=True)

        # Validate status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            self._validate_status_transition(meeting.status, new_status)

        # Update fields
        for field, value in update_data.items():
            if hasattr(meeting, field):
                setattr(meeting, field, value)

        await self.db.flush()
        await self.db.refresh(meeting)

        return meeting

    def _validate_status_transition(
        self,
        current_status: MeetingStatus,
        new_status: MeetingStatus,
    ) -> None:
        """
        Validate meeting status transition.

        Valid transitions:
        - draft -> in_progress
        - in_progress -> completed

        Args:
            current_status: The current meeting status.
            new_status: The desired new status.

        Raises:
            ValueError: If the transition is not allowed.
        """
        valid_transitions = {
            MeetingStatus.DRAFT: {MeetingStatus.IN_PROGRESS},
            MeetingStatus.IN_PROGRESS: {MeetingStatus.COMPLETED},
            MeetingStatus.COMPLETED: set(),  # No transitions from completed
        }

        allowed = valid_transitions.get(current_status, set())
        if new_status != current_status and new_status not in allowed:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}"
            )

    async def delete(self, meeting: Meeting) -> None:
        """
        Soft delete a meeting.

        Args:
            meeting: The meeting to delete.
        """
        meeting.soft_delete()
        await self.db.flush()

    async def restore(self, meeting_id: int) -> Optional[Meeting]:
        """
        Restore a soft-deleted meeting.

        Args:
            meeting_id: The meeting's ID.

        Returns:
            The restored meeting if found and was deleted, None otherwise.
        """
        # Query for deleted meeting (deleted_at is not null)
        query = (
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .where(Meeting.deleted_at.isnot(None))
            .options(selectinload(Meeting.meeting_type))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()

        if not meeting:
            return None

        # Clear deleted_at to restore
        meeting.deleted_at = None
        await self.db.flush()
        await self.db.refresh(meeting)

        return meeting

    async def add_attendee(
        self,
        meeting_id: int,
        data: AttendeeCreate,
    ) -> MeetingAttendee:
        """
        Add an attendee to a meeting.

        Args:
            meeting_id: The meeting's ID.
            data: The attendee data.

        Returns:
            The created attendee.

        Raises:
            ValueError: If the contact is already an attendee.
        """
        # Check if already an attendee
        existing_query = (
            select(MeetingAttendee)
            .where(MeetingAttendee.meeting_id == meeting_id)
            .where(MeetingAttendee.contact_id == data.contact_id)
        )
        existing = await self.db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise ValueError("Contact is already an attendee of this meeting")

        attendee = MeetingAttendee(
            meeting_id=meeting_id,
            contact_id=data.contact_id,
            attended=data.attended,
            speaker_label=data.speaker_label,
        )

        self.db.add(attendee)
        await self.db.flush()

        # Reload with contact relationship
        query = (
            select(MeetingAttendee)
            .where(MeetingAttendee.id == attendee.id)
            .options(selectinload(MeetingAttendee.contact))
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def remove_attendee(
        self,
        meeting_id: int,
        contact_id: int,
    ) -> bool:
        """
        Remove an attendee from a meeting.

        Args:
            meeting_id: The meeting's ID.
            contact_id: The contact's ID.

        Returns:
            True if removed, False if not found.
        """
        query = (
            select(MeetingAttendee)
            .where(MeetingAttendee.meeting_id == meeting_id)
            .where(MeetingAttendee.contact_id == contact_id)
        )
        result = await self.db.execute(query)
        attendee = result.scalar_one_or_none()

        if not attendee:
            return False

        await self.db.delete(attendee)
        await self.db.flush()
        return True

    async def get_meeting_types(self) -> list[MeetingType]:
        """
        Get all meeting types.

        Returns:
            List of meeting types.
        """
        query = (
            select(MeetingType)
            .where(MeetingType.deleted_at.is_(None))
            .order_by(MeetingType.name.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
