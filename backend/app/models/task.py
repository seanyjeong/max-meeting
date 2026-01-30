"""Celery task tracking model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.recording import Recording


class TaskTracking(Base, CreatedAtMixin):
    """Celery task tracking for STT and LLM processing."""

    __tablename__ = "task_trackings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recording_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    recording: Mapped["Recording | None"] = relationship(
        "Recording",
        back_populates="task_trackings",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<TaskTracking(task_id='{self.task_id}', status={self.status})>"
