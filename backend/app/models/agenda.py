"""Agenda related models."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, SoftDeleteMixin
from app.models.enums import AgendaStatus

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.note import ManualNote, Sketch
    from app.models.result import ActionItem, AgendaDiscussion, MeetingDecision


class Agenda(Base, CreatedAtMixin, SoftDeleteMixin):
    """Agenda item model with hierarchical structure."""

    __tablename__ = "agendas"
    __table_args__ = (
        Index("idx_agendas_meeting_order", "meeting_id", "order_num"),
        Index("idx_agendas_parent_order", "parent_id", "order_num"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agendas.id", ondelete="CASCADE"), nullable=True, default=None
    )
    level: Mapped[int] = mapped_column(Integer, default=0)
    order_num: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AgendaStatus] = mapped_column(
        Enum(AgendaStatus, name="agenda_status"),
        default=AgendaStatus.PENDING,
    )
    started_at_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="agendas",
        lazy="joined",
    )
    parent: Mapped["Agenda | None"] = relationship(
        "Agenda",
        remote_side=[id],
        back_populates="children",
        lazy="joined",
    )
    children: Mapped[list["Agenda"]] = relationship(
        "Agenda",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Agenda.order_num",
    )
    questions: Mapped[list["AgendaQuestion"]] = relationship(
        "AgendaQuestion",
        back_populates="agenda",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AgendaQuestion.order_num",
    )
    manual_notes: Mapped[list["ManualNote"]] = relationship(
        "ManualNote",
        back_populates="agenda",
        lazy="selectin",
    )
    sketches: Mapped[list["Sketch"]] = relationship(
        "Sketch",
        back_populates="agenda",
        lazy="selectin",
    )
    discussions: Mapped[list["AgendaDiscussion"]] = relationship(
        "AgendaDiscussion",
        back_populates="agenda",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    decisions: Mapped[list["MeetingDecision"]] = relationship(
        "MeetingDecision",
        back_populates="agenda",
        lazy="selectin",
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        "ActionItem",
        back_populates="agenda",
        lazy="selectin",
    )

    @property
    def is_root(self) -> bool:
        """Check if this agenda is a root-level item (no parent)."""
        return self.parent_id is None

    def __repr__(self) -> str:
        return f"<Agenda(id={self.id}, title='{self.title}', level={self.level}, status={self.status})>"


class AgendaQuestion(Base):
    """LLM-generated question for an agenda item."""

    __tablename__ = "agenda_questions"
    __table_args__ = (
        Index("idx_agenda_questions_agenda", "agenda_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agenda_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agendas.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    order_num: Mapped[int] = mapped_column(Integer, nullable=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    answered: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    agenda: Mapped["Agenda"] = relationship(
        "Agenda",
        back_populates="questions",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<AgendaQuestion(id={self.id}, agenda_id={self.agenda_id})>"
