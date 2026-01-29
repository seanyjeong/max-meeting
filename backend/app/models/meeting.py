"""Meeting related models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, SoftDeleteMixin, TimestampMixin
from app.models.enums import MeetingStatus

if TYPE_CHECKING:
    from app.models.agenda import Agenda
    from app.models.contact import Contact
    from app.models.note import ManualNote, Sketch
    from app.models.recording import Recording, Transcript
    from app.models.result import ActionItem, MeetingDecision, MeetingResult
    from app.models.task import TaskTracking


class MeetingType(Base, CreatedAtMixin, SoftDeleteMixin):
    """Meeting type model (e.g., 북부, 전국, 일산)."""

    __tablename__ = "meeting_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relationships
    meetings: Mapped[list["Meeting"]] = relationship(
        "Meeting",
        back_populates="meeting_type",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<MeetingType(id={self.id}, name='{self.name}')>"


class Meeting(Base, TimestampMixin, SoftDeleteMixin):
    """Meeting model."""

    __tablename__ = "meetings"
    __table_args__ = (
        Index(
            "idx_meetings_type_status",
            "type_id",
            "status",
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "idx_meetings_scheduled",
            "scheduled_at",
            postgresql_using="btree",
            postgresql_ops={"scheduled_at": "DESC"},
            postgresql_where="deleted_at IS NULL",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("meeting_types.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, name="meeting_status"),
        default=MeetingStatus.DRAFT,
    )

    # Relationships
    meeting_type: Mapped["MeetingType | None"] = relationship(
        "MeetingType",
        back_populates="meetings",
        lazy="joined",
    )
    attendees: Mapped[list["MeetingAttendee"]] = relationship(
        "MeetingAttendee",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    agendas: Mapped[list["Agenda"]] = relationship(
        "Agenda",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Agenda.order_num",
    )
    recordings: Mapped[list["Recording"]] = relationship(
        "Recording",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    manual_notes: Mapped[list["ManualNote"]] = relationship(
        "ManualNote",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sketches: Mapped[list["Sketch"]] = relationship(
        "Sketch",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    results: Mapped[list["MeetingResult"]] = relationship(
        "MeetingResult",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    decisions: Mapped[list["MeetingDecision"]] = relationship(
        "MeetingDecision",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        "ActionItem",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    task_trackings: Mapped[list["TaskTracking"]] = relationship(
        "TaskTracking",
        back_populates="meeting",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Meeting(id={self.id}, title='{self.title}', status={self.status})>"


class MeetingAttendee(Base):
    """Meeting attendee association table."""

    __tablename__ = "meeting_attendees"
    __table_args__ = (
        UniqueConstraint("meeting_id", "contact_id", name="uq_meeting_contact"),
        Index("idx_meeting_attendees_meeting", "meeting_id"),
        Index("idx_meeting_attendees_contact", "contact_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id"), nullable=True
    )
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    speaker_label: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="attendees",
        lazy="joined",
    )
    contact: Mapped["Contact | None"] = relationship(
        "Contact",
        back_populates="meeting_attendees",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<MeetingAttendee(meeting_id={self.meeting_id}, contact_id={self.contact_id})>"
