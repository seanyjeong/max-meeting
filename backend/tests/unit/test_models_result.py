"""Tests for Result related models."""

from app.models.result import MeetingResult, MeetingDecision


class TestMeetingResult:
    """Tests for the MeetingResult model."""

    def test_meeting_result_has_correct_tablename(self):
        """MeetingResult should have tablename 'meeting_results'."""
        assert MeetingResult.__tablename__ == "meeting_results"


class TestMeetingDecision:
    """Tests for the MeetingDecision model."""

    def test_meeting_decision_has_correct_tablename(self):
        """MeetingDecision should have tablename 'meeting_decisions'."""
        assert MeetingDecision.__tablename__ == "meeting_decisions"
