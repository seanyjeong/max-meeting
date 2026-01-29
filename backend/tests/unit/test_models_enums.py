"""Tests for ENUM types."""

import enum

from app.models.enums import (
    MeetingStatus,
    AgendaStatus,
    RecordingStatus,
    TaskStatusEnum,
    ActionItemStatus,
    ActionItemPriority,
    DecisionType,
    AuditAction,
    AuditStatus,
)


class TestMeetingStatus:
    """Tests for MeetingStatus enum."""

    def test_meeting_status_is_str_enum(self):
        """MeetingStatus should be a str enum."""
        assert issubclass(MeetingStatus, str)
        assert issubclass(MeetingStatus, enum.Enum)

    def test_meeting_status_has_correct_values(self):
        """MeetingStatus should have draft, in_progress, completed."""
        assert MeetingStatus.DRAFT.value == "draft"
        assert MeetingStatus.IN_PROGRESS.value == "in_progress"
        assert MeetingStatus.COMPLETED.value == "completed"


class TestAgendaStatus:
    """Tests for AgendaStatus enum."""

    def test_agenda_status_has_correct_values(self):
        """AgendaStatus should have pending, in_progress, completed."""
        assert AgendaStatus.PENDING.value == "pending"
        assert AgendaStatus.IN_PROGRESS.value == "in_progress"
        assert AgendaStatus.COMPLETED.value == "completed"


class TestRecordingStatus:
    """Tests for RecordingStatus enum."""

    def test_recording_status_has_correct_values(self):
        """RecordingStatus should have uploaded, processing, completed, failed."""
        assert RecordingStatus.UPLOADED.value == "uploaded"
        assert RecordingStatus.PROCESSING.value == "processing"
        assert RecordingStatus.COMPLETED.value == "completed"
        assert RecordingStatus.FAILED.value == "failed"


class TestTaskStatusEnum:
    """Tests for TaskStatusEnum enum."""

    def test_task_status_has_correct_values(self):
        """TaskStatusEnum should have pending, processing, completed, failed."""
        assert TaskStatusEnum.PENDING.value == "pending"
        assert TaskStatusEnum.PROCESSING.value == "processing"
        assert TaskStatusEnum.COMPLETED.value == "completed"
        assert TaskStatusEnum.FAILED.value == "failed"


class TestActionItemStatus:
    """Tests for ActionItemStatus enum."""

    def test_action_item_status_has_correct_values(self):
        """ActionItemStatus should have pending, in_progress, completed."""
        assert ActionItemStatus.PENDING.value == "pending"
        assert ActionItemStatus.IN_PROGRESS.value == "in_progress"
        assert ActionItemStatus.COMPLETED.value == "completed"


class TestActionItemPriority:
    """Tests for ActionItemPriority enum."""

    def test_action_item_priority_has_correct_values(self):
        """ActionItemPriority should have high, medium, low."""
        assert ActionItemPriority.HIGH.value == "high"
        assert ActionItemPriority.MEDIUM.value == "medium"
        assert ActionItemPriority.LOW.value == "low"


class TestDecisionType:
    """Tests for DecisionType enum."""

    def test_decision_type_has_correct_values(self):
        """DecisionType should have approved, postponed, rejected."""
        assert DecisionType.APPROVED.value == "approved"
        assert DecisionType.POSTPONED.value == "postponed"
        assert DecisionType.REJECTED.value == "rejected"


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_audit_action_has_correct_values(self):
        """AuditAction should have CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT."""
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.READ.value == "READ"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"
        assert AuditAction.LOGIN.value == "LOGIN"
        assert AuditAction.LOGOUT.value == "LOGOUT"


class TestAuditStatus:
    """Tests for AuditStatus enum."""

    def test_audit_status_has_correct_values(self):
        """AuditStatus should have SUCCESS, FAILURE, DENIED."""
        assert AuditStatus.SUCCESS.value == "SUCCESS"
        assert AuditStatus.FAILURE.value == "FAILURE"
        assert AuditStatus.DENIED.value == "DENIED"
