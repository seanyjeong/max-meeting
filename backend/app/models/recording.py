"""Recording and STT related models."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin
from app.models.enums import RecordingStatus

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.task import TaskTracking


class Recording(Base, CreatedAtMixin):
    """Recording file model."""

    __tablename__ = "recordings"
    __table_args__ = (
        Index("idx_recordings_meeting", "meeting_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    safe_filename: Mapped[str] = mapped_column(String(100), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="webm")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus, name="recording_status"),
        default=RecordingStatus.UPLOADED,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="recordings",
        lazy="joined",
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript",
        back_populates="recording",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Transcript.chunk_index",
    )
    task_trackings: Mapped[list["TaskTracking"]] = relationship(
        "TaskTracking",
        back_populates="recording",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Recording(id={self.id}, meeting_id={self.meeting_id}, status={self.status})>"


class Transcript(Base, CreatedAtMixin):
    """STT result model."""

    __tablename__ = "transcripts"
    __table_args__ = (
        Index("idx_transcripts_recording", "recording_id", "chunk_index"),
        Index("idx_transcripts_meeting", "meeting_id"),
        # pg_trgm index for full-text search on transcript_text
        # Note: transcript_text is a generated column in PostgreSQL
        # The index is created via migration, not here
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recording_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False
    )
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    segments: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Note: transcript_text is a generated column in PostgreSQL
    # GENERATED ALWAYS AS (string_agg from segments) STORED
    # This is handled at the database level via migration

    # Relationships
    recording: Mapped["Recording"] = relationship(
        "Recording",
        back_populates="transcripts",
        lazy="joined",
    )
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="transcripts",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Transcript(id={self.id}, recording_id={self.recording_id}, chunk={self.chunk_index})>"
