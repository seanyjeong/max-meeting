"""Note and Sketch related models."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agenda import Agenda
    from app.models.meeting import Meeting


class ManualNote(Base, TimestampMixin):
    """Manual text note during meeting."""

    __tablename__ = "manual_notes"
    __table_args__ = (
        Index("idx_notes_meeting", "meeting_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    agenda_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="manual_notes",
        lazy="joined",
    )
    agenda: Mapped["Agenda | None"] = relationship(
        "Agenda",
        back_populates="manual_notes",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<ManualNote(id={self.id}, meeting_id={self.meeting_id})>"


class Sketch(Base, TimestampMixin):
    """Pencil sketch during meeting."""

    __tablename__ = "sketches"
    __table_args__ = (
        Index("idx_sketches_meeting", "meeting_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    agenda_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id"), nullable=True
    )
    svg_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    json_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timestamp_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="sketches",
        lazy="joined",
    )
    agenda: Mapped["Agenda | None"] = relationship(
        "Agenda",
        back_populates="sketches",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Sketch(id={self.id}, meeting_id={self.meeting_id})>"
