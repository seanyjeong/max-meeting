"""Agenda service for business logic."""

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Agenda, AgendaQuestion, Meeting
from app.models.enums import AgendaStatus
from app.schemas.agenda import (
    AgendaCreate,
    AgendaUpdate,
    QuestionCreate,
    QuestionUpdate,
    ReorderItem,
)


class AgendaService:
    """Service for agenda-related operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_meeting_or_raise(self, meeting_id: int) -> Meeting:
        """Get meeting by ID or raise exception."""
        result = await self.db.execute(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.deleted_at.is_(None),
            )
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            raise ValueError(f"Meeting with id {meeting_id} not found")
        return meeting

    async def get_agenda_or_raise(self, agenda_id: int) -> Agenda:
        """Get agenda by ID or raise exception."""
        result = await self.db.execute(
            select(Agenda)
            .options(selectinload(Agenda.questions))
            .where(
                Agenda.id == agenda_id,
                Agenda.deleted_at.is_(None),
            )
        )
        agenda = result.scalar_one_or_none()
        if not agenda:
            raise ValueError(f"Agenda with id {agenda_id} not found")
        return agenda

    async def list_agendas(
        self,
        meeting_id: int,
        include_deleted: bool = False,
    ) -> list[Agenda]:
        """List all agendas for a meeting."""
        await self.get_meeting_or_raise(meeting_id)

        query = (
            select(Agenda)
            .options(selectinload(Agenda.questions))
            .where(Agenda.meeting_id == meeting_id)
            .order_by(Agenda.order_num)
        )

        if not include_deleted:
            query = query.where(Agenda.deleted_at.is_(None))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_next_order_num(self, meeting_id: int) -> int:
        """Get the next order number for an agenda."""
        result = await self.db.execute(
            select(func.coalesce(func.max(Agenda.order_num), -1) + 1).where(
                Agenda.meeting_id == meeting_id,
                Agenda.deleted_at.is_(None),
            )
        )
        return result.scalar() or 0

    async def create_agenda(
        self,
        meeting_id: int,
        data: AgendaCreate,
    ) -> Agenda:
        """Create a new agenda."""
        await self.get_meeting_or_raise(meeting_id)

        order_num = await self.get_next_order_num(meeting_id)

        agenda = Agenda(
            meeting_id=meeting_id,
            title=data.title,
            description=data.description,
            order_num=order_num,
            status=AgendaStatus.PENDING,
        )

        self.db.add(agenda)
        await self.db.flush()
        await self.db.refresh(agenda)

        return agenda

    async def update_agenda(
        self,
        agenda_id: int,
        data: AgendaUpdate,
    ) -> Agenda:
        """Update an existing agenda."""
        agenda = await self.get_agenda_or_raise(agenda_id)

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(agenda, key, value)

        await self.db.flush()
        await self.db.refresh(agenda)

        return agenda

    async def delete_agenda(self, agenda_id: int) -> bool:
        """Soft delete an agenda."""
        agenda = await self.get_agenda_or_raise(agenda_id)

        from datetime import datetime, timezone

        agenda.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

        return True

    async def reorder_agendas(
        self,
        meeting_id: int,
        items: list[ReorderItem],
    ) -> int:
        """Reorder agendas for a meeting."""
        await self.get_meeting_or_raise(meeting_id)

        updated_count = 0
        for item in items:
            result = await self.db.execute(
                update(Agenda)
                .where(
                    Agenda.id == item.id,
                    Agenda.meeting_id == meeting_id,
                    Agenda.deleted_at.is_(None),
                )
                .values(order_num=item.order_num)
            )
            updated_count += result.rowcount

        return updated_count

    # ============================================
    # Question Operations
    # ============================================

    async def get_question_or_raise(self, question_id: int) -> AgendaQuestion:
        """Get question by ID or raise exception."""
        result = await self.db.execute(
            select(AgendaQuestion).where(AgendaQuestion.id == question_id)
        )
        question = result.scalar_one_or_none()
        if not question:
            raise ValueError(f"Question with id {question_id} not found")
        return question

    async def get_next_question_order(self, agenda_id: int) -> int:
        """Get the next order number for a question."""
        result = await self.db.execute(
            select(func.coalesce(func.max(AgendaQuestion.order_num), -1) + 1).where(
                AgendaQuestion.agenda_id == agenda_id
            )
        )
        return result.scalar() or 0

    async def add_question(
        self,
        agenda_id: int,
        data: QuestionCreate,
    ) -> AgendaQuestion:
        """Add a question to an agenda."""
        await self.get_agenda_or_raise(agenda_id)

        order_num = data.order_num
        if order_num == 0:
            order_num = await self.get_next_question_order(agenda_id)

        question = AgendaQuestion(
            agenda_id=agenda_id,
            question=data.question,
            order_num=order_num,
            is_generated=data.is_generated,
            answered=data.answered,
        )

        self.db.add(question)
        await self.db.flush()
        await self.db.refresh(question)

        return question

    async def update_question(
        self,
        question_id: int,
        data: QuestionUpdate,
    ) -> AgendaQuestion:
        """Update a question."""
        question = await self.get_question_or_raise(question_id)

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(question, key, value)

        await self.db.flush()
        await self.db.refresh(question)

        return question

    async def delete_question(self, question_id: int) -> bool:
        """Delete a question permanently."""
        await self.get_question_or_raise(question_id)

        await self.db.execute(
            delete(AgendaQuestion).where(AgendaQuestion.id == question_id)
        )

        return True
