"""Celery task tracking model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin
from app.models.enums import TaskStatusEnum

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.recording import Recording


class TaskTracking(Base, CreatedAtMixin):
    """Celery task tracking for STT and LLM processing."""

    __tablename__ = "task_tracking"
    __table_args__ = (
        Index("idx_task_tracking_task_id", "task_id"),
        Index("idx_task_tracking_recording", "recording_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recording_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recordings.id"), nullable=True
    )
    meeting_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("meetings.id"), nullable=True
    )
    status: Mapped[TaskStatusEnum] = mapped_column(
        Enum(TaskStatusEnum, name="task_status_enum"),
        default=TaskStatusEnum.PENDING,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    recording: Mapped["Recording | None"] = relationship(
        "Recording",
        back_populates="task_trackings",
        lazy="joined",
    )
    meeting: Mapped["Meeting | None"] = relationship(
        "Meeting",
        back_populates="task_trackings",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<TaskTracking(task_id='{self.task_id}', status={self.status})>"
