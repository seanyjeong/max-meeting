"""ENUM types for the database schema."""

import enum


class MeetingStatus(str, enum.Enum):
    """Status of a meeting."""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AgendaStatus(str, enum.Enum):
    """Status of an agenda item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RecordingStatus(str, enum.Enum):
    """Status of a recording."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatusEnum(str, enum.Enum):
    """Status of a Celery task."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionItemStatus(str, enum.Enum):
    """Status of an action item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ActionItemPriority(str, enum.Enum):
    """Priority level of an action item."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionType(str, enum.Enum):
    """Type of decision made in a meeting."""

    APPROVED = "approved"
    POSTPONED = "postponed"
    REJECTED = "rejected"


class AuditAction(str, enum.Enum):
    """Type of audit action."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"


class AuditStatus(str, enum.Enum):
    """Status of an audit action."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"
