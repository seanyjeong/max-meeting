"""Tests for Meeting related models."""

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.meeting import MeetingType, Meeting, MeetingAttendee


class TestMeetingType:
    """Tests for the MeetingType model."""

    def test_meeting_type_is_base_model(self):
        """MeetingType should inherit from Base."""
        assert issubclass(MeetingType, Base)

    def test_meeting_type_has_correct_tablename(self):
        """MeetingType should have tablename 'meeting_types'."""
        assert MeetingType.__tablename__ == "meeting_types"


class TestMeeting:
    """Tests for the Meeting model."""

    def test_meeting_has_correct_tablename(self):
        """Meeting should have tablename 'meetings'."""
        assert Meeting.__tablename__ == "meetings"


class TestMeetingAttendee:
    """Tests for the MeetingAttendee model."""

    def test_meeting_attendee_has_correct_tablename(self):
        """MeetingAttendee should have tablename 'meeting_attendees'."""
        assert MeetingAttendee.__tablename__ == "meeting_attendees"
