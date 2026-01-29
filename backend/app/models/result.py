"""Meeting result related models."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin
from app.models.enums import ActionItemPriority, ActionItemStatus, DecisionType

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

    def __repr__(self) -> str:
        return f"<MeetingResult(id={self.id}, meeting_id={self.meeting_id}, version={self.version})>"


class MeetingDecision(Base, CreatedAtMixin):
    """Decision made during a meeting."""

    __tablename__ = "meeting_decisions"
    __table_args__ = (
        Index("idx_meeting_decisions_meeting", "meeting_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    agenda_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    decision_type: Mapped[DecisionType] = mapped_column(
        Enum(DecisionType, name="decision_type"),
        default=DecisionType.APPROVED,
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
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


class AgendaDiscussion(Base, TimestampMixin):
    """Discussion content for an agenda item."""

    __tablename__ = "agenda_discussions"
    __table_args__ = (
        Index("idx_agenda_discussions_agenda", "agenda_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agenda_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agendas.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_llm_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    agenda: Mapped["Agenda"] = relationship(
        "Agenda",
        back_populates="discussions",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<AgendaDiscussion(id={self.id}, agenda_id={self.agenda_id})>"


class ActionItem(Base, CreatedAtMixin):
    """Action item from a meeting."""

    __tablename__ = "action_items"
    __table_args__ = (
        Index("idx_action_items_meeting", "meeting_id", "status"),
        Index("idx_action_items_assignee", "assignee_id", "due_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    agenda_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id"), nullable=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[ActionItemPriority] = mapped_column(
        Enum(ActionItemPriority, name="action_item_priority"),
        default=ActionItemPriority.MEDIUM,
    )
    status: Mapped[ActionItemStatus] = mapped_column(
        Enum(ActionItemStatus, name="action_item_status"),
        default=ActionItemStatus.PENDING,
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
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
