"""SQLAlchemy models for MAX Meeting."""

from app.models.base import Base, CreatedAtMixin, SoftDeleteMixin, TimestampMixin
from app.models.enums import (
    ActionItemPriority,
    ActionItemStatus,
    AgendaStatus,
    AuditAction,
    AuditStatus,
    DecisionType,
    MeetingStatus,
    RecordingStatus,
    TaskStatusEnum,
)

# Import models in dependency order to avoid circular imports
from app.models.contact import Contact
from app.models.meeting import Meeting, MeetingAttendee, MeetingType
from app.models.agenda import Agenda, AgendaQuestion
from app.models.recording import Recording, Transcript
from app.models.note import ManualNote, Sketch
from app.models.result import ActionItem, AgendaDiscussion, MeetingDecision, MeetingResult
from app.models.task import TaskTracking
from app.models.audit import AuditLog

__all__ = [
    # Base classes and mixins
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "CreatedAtMixin",
    # Enums
    "MeetingStatus",
    "AgendaStatus",
    "RecordingStatus",
    "TaskStatusEnum",
    "ActionItemStatus",
    "ActionItemPriority",
    "DecisionType",
    "AuditAction",
    "AuditStatus",
    # Contact
    "Contact",
    # Meeting
    "MeetingType",
    "Meeting",
    "MeetingAttendee",
    # Agenda
    "Agenda",
    "AgendaQuestion",
    # Recording
    "Recording",
    "Transcript",
    # Note
    "ManualNote",
    "Sketch",
    # Result
    "MeetingResult",
    "MeetingDecision",
    "AgendaDiscussion",
    "ActionItem",
    # Task
    "TaskTracking",
    # Audit
    "AuditLog",
]
