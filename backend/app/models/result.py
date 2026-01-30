"""Meeting result related models."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.agenda import Agenda
    from app.models.contact import Contact
    from app.models.meeting import Meeting


class MeetingResult(Base, TimestampMixin):
    """Meeting result summary with version control."""

    __tablename__ = "meeting_results"
    __table_args__ = (
        UniqueConstraint("meeting_id", "version", name="uq_meeting_result_version"),
        # pg_trgm index for full-text search on summary
        Index(
            "idx_meeting_results_summary_trgm",
            "summary",
            postgresql_using="gin",
            postgresql_ops={"summary": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="results",
        lazy="joined",
    )
    decisions: Mapped[list["MeetingDecision"]] = relationship(
        "MeetingDecision",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    discussions: Mapped[list["AgendaDiscussion"]] = relationship(
        "AgendaDiscussion",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        "ActionItem",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<MeetingResult(id={self.id}, meeting_id={self.meeting_id}, version={self.version})>"


class MeetingDecision(Base, CreatedAtMixin):
    """Decision made during a meeting."""

    __tablename__ = "meeting_decisions"
    __table_args__ = (
        Index("idx_meeting_decisions_result", "result_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_results.id", ondelete="CASCADE"), nullable=False
    )
    agenda_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id", ondelete="SET NULL"), nullable=True
    )
    decision_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    result: Mapped["MeetingResult"] = relationship(
        "MeetingResult",
        back_populates="decisions",
        lazy="joined",
    )
    agenda: Mapped["Agenda | None"] = relationship(
        "Agenda",
        back_populates="decisions",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<MeetingDecision(id={self.id}, type={self.decision_type})>"


class AgendaDiscussion(Base, CreatedAtMixin):
    """Discussion content for an agenda item."""

    __tablename__ = "agenda_discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_results.id", ondelete="CASCADE"), nullable=False
    )
    agenda_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agendas.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    result: Mapped["MeetingResult"] = relationship(
        "MeetingResult",
        back_populates="discussions",
        lazy="joined",
    )
    agenda: Mapped["Agenda"] = relationship(
        "Agenda",
        back_populates="discussions",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<AgendaDiscussion(id={self.id}, agenda_id={self.agenda_id})>"


class ActionItem(Base, TimestampMixin):
    """Action item from a meeting."""

    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("meeting_results.id", ondelete="CASCADE"), nullable=True
    )
    agenda_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id", ondelete="SET NULL"), nullable=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    meeting_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("meetings.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    result: Mapped["MeetingResult | None"] = relationship(
        "MeetingResult",
        back_populates="action_items",
        lazy="joined",
    )
    meeting: Mapped["Meeting | None"] = relationship(
        "Meeting",
        back_populates="action_items",
        lazy="joined",
    )
    agenda: Mapped["Agenda | None"] = relationship(
        "Agenda",
        back_populates="action_items",
        lazy="joined",
    )
    assignee: Mapped["Contact | None"] = relationship(
        "Contact",
        back_populates="assigned_action_items",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<ActionItem(id={self.id}, status={self.status}, priority={self.priority})>"
