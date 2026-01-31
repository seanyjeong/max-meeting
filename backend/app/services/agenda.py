"""Agenda service for business logic."""

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Agenda, AgendaQuestion, Meeting
from app.models.enums import AgendaStatus
from app.schemas.agenda import (
    AgendaCreate,
    AgendaUpdate,
    AgendaMoveRequest,
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
        """List all agendas for a meeting as a flat list."""
        await self.get_meeting_or_raise(meeting_id)

        query = (
            select(Agenda)
            .options(
                selectinload(Agenda.questions),
                selectinload(Agenda.children),
            )
            .where(Agenda.meeting_id == meeting_id)
            .order_by(Agenda.level, Agenda.order_num)
        )

        if not include_deleted:
            query = query.where(Agenda.deleted_at.is_(None))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_agendas_tree(
        self,
        meeting_id: int,
        include_deleted: bool = False,
    ) -> list[Agenda]:
        """List all agendas for a meeting as a tree (root level only with children loaded)."""
        await self.get_meeting_or_raise(meeting_id)

        # Get all agendas first (load up to 3 levels deep)
        # time_segments is JSONB column, auto-loaded. Only relationships need selectinload.
        query = (
            select(Agenda)
            .options(
                selectinload(Agenda.questions),
                # Level 1 children + their questions
                selectinload(Agenda.children).selectinload(Agenda.questions),
                # Level 2 children (grandchildren) + their questions
                selectinload(Agenda.children)
                    .selectinload(Agenda.children)
                    .selectinload(Agenda.questions),
            )
            .where(
                Agenda.meeting_id == meeting_id,
                Agenda.parent_id.is_(None),  # Only root level
            )
            .order_by(Agenda.order_num)
        )

        if not include_deleted:
            query = query.where(Agenda.deleted_at.is_(None))

        result = await self.db.execute(query)
        root_agendas = list(result.scalars().all())

        # Recursively load children (SQLAlchemy should have loaded them via selectinload)
        return root_agendas

    async def get_next_order_num(
        self, meeting_id: int, parent_id: int | None = None
    ) -> int:
        """Get the next order number for an agenda within a parent."""
        query = select(func.coalesce(func.max(Agenda.order_num), -1) + 1).where(
            Agenda.meeting_id == meeting_id,
            Agenda.deleted_at.is_(None),
        )
        if parent_id is None:
            query = query.where(Agenda.parent_id.is_(None))
        else:
            query = query.where(Agenda.parent_id == parent_id)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_parent_level(self, parent_id: int | None) -> int:
        """Get the level of a parent agenda (returns 0 if parent is None)."""
        if parent_id is None:
            return 0
        parent = await self.get_agenda_or_raise(parent_id)
        return parent.level + 1

    async def create_agenda(
        self,
        meeting_id: int,
        data: AgendaCreate,
    ) -> Agenda:
        """Create a new agenda with optional parent."""
        await self.get_meeting_or_raise(meeting_id)

        # Validate parent exists and belongs to the same meeting
        parent_id = data.parent_id
        if parent_id is not None:
            parent = await self.get_agenda_or_raise(parent_id)
            if parent.meeting_id != meeting_id:
                raise ValueError("Parent agenda must belong to the same meeting")

        order_num = await self.get_next_order_num(meeting_id, parent_id)
        level = await self.get_parent_level(parent_id)

        agenda = Agenda(
            meeting_id=meeting_id,
            parent_id=parent_id,
            level=level,
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
        """Reorder agendas for a meeting (within the same parent level)."""
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

    async def move_agenda(
        self,
        agenda_id: int,
        data: AgendaMoveRequest,
    ) -> Agenda:
        """Move an agenda to a new parent and/or position."""
        agenda = await self.get_agenda_or_raise(agenda_id)
        new_parent_id = data.new_parent_id

        # Validate new parent
        if new_parent_id is not None:
            new_parent = await self.get_agenda_or_raise(new_parent_id)
            # Prevent moving to own descendant (would create cycle)
            if await self._is_descendant(new_parent_id, agenda_id):
                raise ValueError("Cannot move agenda to its own descendant")
            # Ensure same meeting
            if new_parent.meeting_id != agenda.meeting_id:
                raise ValueError("Cannot move agenda to a different meeting")

        # Calculate new level
        new_level = await self.get_parent_level(new_parent_id)

        # Update level for all descendants recursively
        level_diff = new_level - agenda.level
        if level_diff != 0:
            await self._update_descendant_levels(agenda_id, level_diff)

        # Update the agenda itself
        agenda.parent_id = new_parent_id
        agenda.level = new_level
        agenda.order_num = data.new_order_num

        await self.db.flush()
        await self.db.refresh(agenda)

        return agenda

    async def _is_descendant(self, potential_descendant_id: int, ancestor_id: int) -> bool:
        """Check if potential_descendant is a descendant of ancestor."""
        # Get all descendants of ancestor
        result = await self.db.execute(
            select(Agenda.id).where(Agenda.parent_id == ancestor_id)
        )
        child_ids = list(result.scalars().all())

        if potential_descendant_id in child_ids:
            return True

        for child_id in child_ids:
            if await self._is_descendant(potential_descendant_id, child_id):
                return True

        return False

    async def _update_descendant_levels(self, parent_id: int, level_diff: int) -> None:
        """Recursively update levels of all descendants."""
        result = await self.db.execute(
            select(Agenda).where(Agenda.parent_id == parent_id)
        )
        children = list(result.scalars().all())

        for child in children:
            child.level += level_diff
            await self._update_descendant_levels(child.id, level_diff)

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
