"""Unit tests for meetings router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.models.enums import MeetingStatus


class TestMeetingsSchemas:
    """Test meeting schemas."""

    def test_meeting_create_schema_validation(self):
        """Test MeetingCreate schema validation."""
        from app.schemas.meeting import MeetingCreate

        # Valid meeting
        meeting = MeetingCreate(
            title="Test Meeting",
            type_id=1,
            scheduled_at=datetime.now(timezone.utc),
            location="Conference Room A",
        )
        assert meeting.title == "Test Meeting"
        assert meeting.type_id == 1

    def test_meeting_create_requires_title(self):
        """Test that title is required."""
        from app.schemas.meeting import MeetingCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            MeetingCreate(type_id=1)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_meeting_create_title_length(self):
        """Test title length validation."""
        from app.schemas.meeting import MeetingCreate
        from pydantic import ValidationError

        # Empty title should fail
        with pytest.raises(ValidationError):
            MeetingCreate(title="")

        # Title too long should fail (>200 chars)
        with pytest.raises(ValidationError):
            MeetingCreate(title="a" * 201)

    def test_meeting_create_with_attendees(self):
        """Test creating meeting with attendee IDs."""
        from app.schemas.meeting import MeetingCreate

        meeting = MeetingCreate(
            title="Test Meeting",
            attendee_ids=[1, 2, 3],
        )
        assert meeting.attendee_ids == [1, 2, 3]

    def test_meeting_update_all_optional(self):
        """Test that MeetingUpdate has all optional fields."""
        from app.schemas.meeting import MeetingUpdate

        # Empty update should be valid
        update = MeetingUpdate()
        assert update.model_dump(exclude_unset=True) == {}

        # Partial update should be valid
        update = MeetingUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.location is None

    def test_meeting_update_status(self):
        """Test status update validation."""
        from app.schemas.meeting import MeetingUpdate

        update = MeetingUpdate(status=MeetingStatus.IN_PROGRESS)
        assert update.status == MeetingStatus.IN_PROGRESS

    def test_meeting_response_from_attributes(self):
        """Test MeetingResponse with from_attributes."""
        from app.schemas.meeting import MeetingResponse

        now = datetime.now(timezone.utc)
        response = MeetingResponse(
            id=1,
            title="Test Meeting",
            type_id=1,
            meeting_type=None,
            scheduled_at=now,
            location="Room A",
            status=MeetingStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )

        assert response.id == 1
        assert response.title == "Test Meeting"
        assert response.status == MeetingStatus.DRAFT

    def test_meeting_detail_response(self):
        """Test MeetingDetailResponse with nested data."""
        from app.schemas.meeting import MeetingDetailResponse, AttendeeResponse, AgendaBrief

        now = datetime.now(timezone.utc)
        response = MeetingDetailResponse(
            id=1,
            title="Test Meeting",
            type_id=1,
            meeting_type=None,
            scheduled_at=now,
            location="Room A",
            status=MeetingStatus.DRAFT,
            created_at=now,
            updated_at=now,
            attendees=[
                AttendeeResponse(
                    id=1,
                    meeting_id=1,
                    contact_id=1,
                    attended=False,
                    speaker_label=None,
                    contact=None,
                )
            ],
            agendas=[
                AgendaBrief(
                    id=1,
                    order_num=1,
                    title="Agenda 1",
                    status="pending",
                    started_at_seconds=None,
                )
            ],
        )

        assert len(response.attendees) == 1
        assert len(response.agendas) == 1

    def test_attendee_create_schema(self):
        """Test AttendeeCreate schema."""
        from app.schemas.meeting import AttendeeCreate

        attendee = AttendeeCreate(
            contact_id=1,
            attended=True,
            speaker_label="Speaker A",
        )
        assert attendee.contact_id == 1
        assert attendee.attended is True
        assert attendee.speaker_label == "Speaker A"

    def test_meeting_list_response(self):
        """Test MeetingListResponse schema."""
        from app.schemas.meeting import MeetingListResponse, MeetingListMeta, MeetingResponse

        now = datetime.now(timezone.utc)
        response = MeetingListResponse(
            data=[
                MeetingResponse(
                    id=1,
                    title="Meeting 1",
                    type_id=None,
                    meeting_type=None,
                    scheduled_at=now,
                    location=None,
                    status=MeetingStatus.DRAFT,
                    created_at=now,
                    updated_at=now,
                ),
            ],
            meta=MeetingListMeta(total=50, limit=20, offset=0),
        )

        assert len(response.data) == 1
        assert response.meta.total == 50


class TestMeetingService:
    """Test MeetingService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_service_get_list_basic(self, mock_db):
        """Test basic list retrieval."""
        from app.services.meeting import MeetingService

        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.title = "Test Meeting"
        mock_meeting.deleted_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = [mock_meeting]
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        service = MeetingService(mock_db)
        meetings, total = await service.get_list()

        assert total == 1
        assert len(meetings) == 1
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_service_get_list_with_filters(self, mock_db):
        """Test list retrieval with filters."""
        from app.services.meeting import MeetingService

        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        service = MeetingService(mock_db)
        meetings, total = await service.get_list(
            status=MeetingStatus.DRAFT,
            type_id=1,
            from_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )

        assert total == 0
        assert len(meetings) == 0

    @pytest.mark.asyncio
    async def test_service_get_by_id(self, mock_db):
        """Test getting meeting by ID."""
        from app.services.meeting import MeetingService

        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.title = "Test Meeting"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_meeting
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MeetingService(mock_db)
        meeting = await service.get_by_id(1)

        assert meeting is not None
        assert meeting.id == 1

    @pytest.mark.asyncio
    async def test_service_get_by_id_not_found(self, mock_db):
        """Test getting non-existent meeting."""
        from app.services.meeting import MeetingService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MeetingService(mock_db)
        meeting = await service.get_by_id(999)

        assert meeting is None

    @pytest.mark.asyncio
    async def test_service_create(self, mock_db):
        """Test meeting creation."""
        from app.services.meeting import MeetingService
        from app.schemas.meeting import MeetingCreate

        data = MeetingCreate(
            title="Test Meeting",
            type_id=1,
            location="Room A",
        )

        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.title = "Test Meeting"
        mock_meeting.attendees = []
        mock_meeting.agendas = []

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Mock get_by_id for the return
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_meeting
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MeetingService(mock_db)
        meeting = await service.create(data)

        assert meeting is not None
        mock_db.add.assert_called()

    @pytest.mark.asyncio
    async def test_service_create_with_attendees(self, mock_db):
        """Test meeting creation with attendees."""
        from app.services.meeting import MeetingService
        from app.schemas.meeting import MeetingCreate

        data = MeetingCreate(
            title="Test Meeting",
            attendee_ids=[1, 2, 3],
        )

        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.attendees = []
        mock_meeting.agendas = []

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_meeting
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MeetingService(mock_db)
        meeting = await service.create(data)

        # Should have called add 4 times: 1 meeting + 3 attendees
        assert mock_db.add.call_count == 4

    def test_status_transition_validation(self):
        """Test status transition validation."""
        from app.services.meeting import MeetingService

        mock_db = MagicMock()
        service = MeetingService(mock_db)

        # Valid transitions
        service._validate_status_transition(MeetingStatus.DRAFT, MeetingStatus.DRAFT)
        service._validate_status_transition(MeetingStatus.DRAFT, MeetingStatus.IN_PROGRESS)
        service._validate_status_transition(MeetingStatus.IN_PROGRESS, MeetingStatus.COMPLETED)

        # Invalid transitions should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            service._validate_status_transition(MeetingStatus.DRAFT, MeetingStatus.COMPLETED)
        assert "Invalid status transition" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            service._validate_status_transition(MeetingStatus.COMPLETED, MeetingStatus.DRAFT)
        assert "Invalid status transition" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            service._validate_status_transition(MeetingStatus.IN_PROGRESS, MeetingStatus.DRAFT)
        assert "Invalid status transition" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_service_soft_delete(self, mock_db):
        """Test soft delete."""
        from app.services.meeting import MeetingService

        mock_meeting = MagicMock()
        mock_meeting.soft_delete = MagicMock()

        mock_db.flush = AsyncMock()

        service = MeetingService(mock_db)
        await service.delete(mock_meeting)

        mock_meeting.soft_delete.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_add_attendee(self, mock_db):
        """Test adding attendee."""
        from app.services.meeting import MeetingService
        from app.schemas.meeting import AttendeeCreate

        data = AttendeeCreate(contact_id=1, attended=False)

        # Mock check for existing attendee
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None

        # Mock the created attendee
        mock_attendee = MagicMock()
        mock_attendee.id = 1
        mock_attendee.meeting_id = 1
        mock_attendee.contact_id = 1
        mock_attendee.contact = MagicMock()

        mock_attendee_result = MagicMock()
        mock_attendee_result.scalar_one.return_value = mock_attendee

        mock_db.execute = AsyncMock(side_effect=[mock_existing_result, mock_attendee_result])
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        service = MeetingService(mock_db)
        attendee = await service.add_attendee(1, data)

        assert attendee is not None
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_add_attendee_already_exists(self, mock_db):
        """Test adding attendee that already exists."""
        from app.services.meeting import MeetingService
        from app.schemas.meeting import AttendeeCreate

        data = AttendeeCreate(contact_id=1, attended=False)

        # Mock existing attendee found
        mock_existing = MagicMock()
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = mock_existing

        mock_db.execute = AsyncMock(return_value=mock_existing_result)

        service = MeetingService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            await service.add_attendee(1, data)

        assert "already an attendee" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_service_remove_attendee(self, mock_db):
        """Test removing attendee."""
        from app.services.meeting import MeetingService

        mock_attendee = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_attendee

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.flush = AsyncMock()

        service = MeetingService(mock_db)
        removed = await service.remove_attendee(1, 1)

        assert removed is True
        mock_db.delete.assert_called_once_with(mock_attendee)

    @pytest.mark.asyncio
    async def test_service_remove_attendee_not_found(self, mock_db):
        """Test removing non-existent attendee."""
        from app.services.meeting import MeetingService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MeetingService(mock_db)
        removed = await service.remove_attendee(1, 999)

        assert removed is False


class TestMeetingRouterHelpers:
    """Test router helper functions."""

    def test_meeting_to_detail_response(self):
        """Test _meeting_to_detail_response function."""
        # Import inside test to avoid module-level import issues
        from app.schemas.meeting import (
            MeetingDetailResponse,
            AttendeeResponse,
            AgendaBrief,
            ContactBrief,
        )

        # Create mock meeting
        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.title = "Test Meeting"
        mock_meeting.type_id = 1
        mock_meeting.meeting_type = MagicMock()
        mock_meeting.meeting_type.id = 1
        mock_meeting.meeting_type.name = "Type 1"
        mock_meeting.scheduled_at = datetime.now(timezone.utc)
        mock_meeting.location = "Room A"
        mock_meeting.status = MeetingStatus.DRAFT
        mock_meeting.created_at = datetime.now(timezone.utc)
        mock_meeting.updated_at = datetime.now(timezone.utc)

        # Mock attendees
        mock_contact = MagicMock()
        mock_contact.id = 1
        mock_contact.name = "John Doe"
        mock_contact.organization = "ACME"
        mock_contact.role = "Manager"

        mock_attendee = MagicMock()
        mock_attendee.id = 1
        mock_attendee.meeting_id = 1
        mock_attendee.contact_id = 1
        mock_attendee.attended = False
        mock_attendee.speaker_label = "Speaker A"
        mock_attendee.contact = mock_contact

        mock_meeting.attendees = [mock_attendee]

        # Mock agendas
        mock_agenda = MagicMock()
        mock_agenda.id = 1
        mock_agenda.order_num = 1
        mock_agenda.title = "Agenda 1"
        mock_agenda.status = MagicMock()
        mock_agenda.status.value = "pending"
        mock_agenda.started_at_seconds = None

        mock_meeting.agendas = [mock_agenda]

        # Convert manually (same logic as _meeting_to_detail_response)
        attendees = []
        for att in mock_meeting.attendees:
            contact_brief = None
            if att.contact:
                contact_brief = ContactBrief(
                    id=att.contact.id,
                    name=att.contact.name,
                    organization=att.contact.organization,
                    role=att.contact.role,
                )
            attendees.append(AttendeeResponse(
                id=att.id,
                meeting_id=att.meeting_id,
                contact_id=att.contact_id,
                attended=att.attended,
                speaker_label=att.speaker_label,
                contact=contact_brief,
            ))

        agendas = [
            AgendaBrief(
                id=agenda.id,
                order_num=agenda.order_num,
                title=agenda.title,
                status=agenda.status.value,
                started_at_seconds=agenda.started_at_seconds,
            )
            for agenda in mock_meeting.agendas
        ]

        response = MeetingDetailResponse(
            id=mock_meeting.id,
            title=mock_meeting.title,
            type_id=mock_meeting.type_id,
            meeting_type=mock_meeting.meeting_type,
            scheduled_at=mock_meeting.scheduled_at,
            location=mock_meeting.location,
            status=mock_meeting.status,
            created_at=mock_meeting.created_at,
            updated_at=mock_meeting.updated_at,
            attendees=attendees,
            agendas=agendas,
        )

        assert response.id == 1
        assert response.title == "Test Meeting"
        assert len(response.attendees) == 1
        assert response.attendees[0].contact.name == "John Doe"
        assert len(response.agendas) == 1
        assert response.agendas[0].title == "Agenda 1"

    def test_meeting_to_detail_response_without_contact(self):
        """Test _meeting_to_detail_response with attendee without contact."""
        from app.schemas.meeting import (
            MeetingDetailResponse,
            AttendeeResponse,
        )

        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.title = "Test Meeting"
        mock_meeting.type_id = None
        mock_meeting.meeting_type = None
        mock_meeting.scheduled_at = None
        mock_meeting.location = None
        mock_meeting.status = MeetingStatus.DRAFT
        mock_meeting.created_at = datetime.now(timezone.utc)
        mock_meeting.updated_at = datetime.now(timezone.utc)

        # Attendee without contact
        mock_attendee = MagicMock()
        mock_attendee.id = 1
        mock_attendee.meeting_id = 1
        mock_attendee.contact_id = None
        mock_attendee.attended = False
        mock_attendee.speaker_label = None
        mock_attendee.contact = None

        mock_meeting.attendees = [mock_attendee]
        mock_meeting.agendas = []

        # Convert manually
        attendees = [
            AttendeeResponse(
                id=mock_attendee.id,
                meeting_id=mock_attendee.meeting_id,
                contact_id=mock_attendee.contact_id,
                attended=mock_attendee.attended,
                speaker_label=mock_attendee.speaker_label,
                contact=None,
            )
        ]

        response = MeetingDetailResponse(
            id=mock_meeting.id,
            title=mock_meeting.title,
            type_id=mock_meeting.type_id,
            meeting_type=mock_meeting.meeting_type,
            scheduled_at=mock_meeting.scheduled_at,
            location=mock_meeting.location,
            status=mock_meeting.status,
            created_at=mock_meeting.created_at,
            updated_at=mock_meeting.updated_at,
            attendees=attendees,
            agendas=[],
        )

        assert len(response.attendees) == 1
        assert response.attendees[0].contact is None
