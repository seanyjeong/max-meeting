"""
Processing log models for STT and LLM operations.

Tracks processing events for monitoring and debugging.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class STTLog(Base):
    """Log entry for STT processing events."""

    __tablename__ = "stt_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recording_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recordings.id"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(String(255))

    # Processing info
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'start', 'chunk_complete', 'complete', 'error'
    chunk_index: Mapped[int | None] = mapped_column(Integer)
    total_chunks: Mapped[int | None] = mapped_column(Integer)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Audio info
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float)
    audio_file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    # Result
    transcript_length: Mapped[int | None] = mapped_column(Integer)
    word_count: Mapped[int | None] = mapped_column(Integer)

    # Error info
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    error_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_stt_logs_recording", "recording_id"),
        Index("idx_stt_logs_created", "created_at"),
        Index("idx_stt_logs_event", "event_type"),
    )


class LLMLog(Base):
    """Log entry for LLM API call events."""

    __tablename__ = "llm_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("meetings.id")
    )
    agenda_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id")
    )
    task_id: Mapped[str | None] = mapped_column(String(255))

    # Request info
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'start', 'complete', 'error'
    operation: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'summary', 'questions', 'agenda_parse'
    provider: Mapped[str | None] = mapped_column(String(50))  # 'gemini', 'openai'
    model: Mapped[str | None] = mapped_column(String(100))

    # Input metrics
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    prompt_length: Mapped[int | None] = mapped_column(Integer)

    # Output metrics
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    response_length: Mapped[int | None] = mapped_column(Integer)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Cost estimation
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float)

    # Error info
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    error_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_llm_logs_meeting", "meeting_id"),
        Index("idx_llm_logs_created", "created_at"),
        Index("idx_llm_logs_operation", "operation"),
    )
