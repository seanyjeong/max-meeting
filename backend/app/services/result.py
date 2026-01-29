"""Meeting result service for business logic."""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ActionItem,
    Meeting,
    MeetingDecision,
    MeetingResult,
)
from app.models.enums import ActionItemStatus
from app.schemas.result import (
    ActionItemCreate,
    ActionItemUpdate,
    ResultCreate,
    ResultUpdate,
)


class ResultService:
    """Service for meeting result operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_meeting_or_raise(self, meeting_id: int) -> Meeting:
        """Get meeting by ID or raise exception."""
        result = await self.db.execute(
            select(Meeting)
            .options(
                selectinload(Meeting.results),
                selectinload(Meeting.decisions),
                selectinload(Meeting.action_items),
            )
            .where(
                Meeting.id == meeting_id,
                Meeting.deleted_at.is_(None),
            )
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            raise ValueError(f"Meeting with id {meeting_id} not found")
        return meeting

    async def get_result_or_raise(
        self,
        result_id: int,
        include_relations: bool = False,
    ) -> MeetingResult:
        """Get result by ID or raise exception."""
        query = select(MeetingResult).where(MeetingResult.id == result_id)

        result = await self.db.execute(query)
        meeting_result = result.scalar_one_or_none()
        if not meeting_result:
            raise ValueError(f"Result with id {result_id} not found")
        return meeting_result

    async def get_action_item_or_raise(self, action_item_id: int) -> ActionItem:
        """Get action item by ID or raise exception."""
        result = await self.db.execute(
            select(ActionItem).where(ActionItem.id == action_item_id)
        )
        action_item = result.scalar_one_or_none()
        if not action_item:
            raise ValueError(f"Action item with id {action_item_id} not found")
        return action_item

    # ============================================
    # Result Operations
    # ============================================

    async def list_results(self, meeting_id: int) -> list[MeetingResult]:
        """List all result versions for a meeting."""
        await self.get_meeting_or_raise(meeting_id)

        result = await self.db.execute(
            select(MeetingResult)
            .where(MeetingResult.meeting_id == meeting_id)
            .order_by(MeetingResult.version.desc())
        )
        return list(result.scalars().all())

    async def get_result(
        self,
        result_id: int,
        include_relations: bool = True,
    ) -> MeetingResult:
        """Get a specific result."""
        return await self.get_result_or_raise(result_id, include_relations)

    async def get_latest_result(self, meeting_id: int) -> MeetingResult | None:
        """Get the latest result version for a meeting."""
        result = await self.db.execute(
            select(MeetingResult)
            .where(MeetingResult.meeting_id == meeting_id)
            .order_by(MeetingResult.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_version(self, meeting_id: int) -> int:
        """Get the next version number for results."""
        result = await self.db.execute(
            select(func.coalesce(func.max(MeetingResult.version), 0) + 1).where(
                MeetingResult.meeting_id == meeting_id
            )
        )
        return result.scalar() or 1

    async def create_result(
        self,
        meeting_id: int,
        data: ResultCreate,
    ) -> MeetingResult:
        """Create a new result version."""
        await self.get_meeting_or_raise(meeting_id)

        version = await self.get_next_version(meeting_id)

        meeting_result = MeetingResult(
            meeting_id=meeting_id,
            summary=data.summary,
            version=version,
            is_verified=False,
        )

        self.db.add(meeting_result)
        await self.db.flush()
        await self.db.refresh(meeting_result)

        return meeting_result

    async def update_result(
        self,
        result_id: int,
        data: ResultUpdate,
    ) -> MeetingResult:
        """Update an existing result."""
        meeting_result = await self.get_result_or_raise(result_id)

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if key == "key_points":
                # key_points could be stored in a separate table or JSON field
                # For now, we skip it as MeetingResult doesn't have this field
                continue
            setattr(meeting_result, key, value)

        await self.db.flush()
        await self.db.refresh(meeting_result)

        return meeting_result

    async def verify_result(self, result_id: int) -> MeetingResult:
        """Mark a result as verified."""
        meeting_result = await self.get_result_or_raise(result_id)

        meeting_result.is_verified = True
        meeting_result.verified_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(meeting_result)

        return meeting_result

    # ============================================
    # Action Item Operations
    # ============================================

    async def list_action_items(self, meeting_id: int) -> list[ActionItem]:
        """List all action items for a meeting."""
        await self.get_meeting_or_raise(meeting_id)

        result = await self.db.execute(
            select(ActionItem)
            .where(ActionItem.meeting_id == meeting_id)
            .order_by(ActionItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_action_item(
        self,
        meeting_id: int,
        data: ActionItemCreate,
    ) -> ActionItem:
        """Create a new action item."""
        await self.get_meeting_or_raise(meeting_id)

        action_item = ActionItem(
            meeting_id=meeting_id,
            agenda_id=data.agenda_id,
            assignee_id=data.assignee_id,
            content=data.content,
            due_date=data.due_date,
            priority=data.priority,
            status=ActionItemStatus.PENDING,
        )

        self.db.add(action_item)
        await self.db.flush()
        await self.db.refresh(action_item)

        return action_item

    async def update_action_item(
        self,
        action_item_id: int,
        data: ActionItemUpdate,
    ) -> ActionItem:
        """Update an action item."""
        action_item = await self.get_action_item_or_raise(action_item_id)

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(action_item, key, value)

        # Update completed_at if status changed to completed
        if data.status == ActionItemStatus.COMPLETED:
            action_item.completed_at = datetime.now(timezone.utc)
        elif data.status and data.status != ActionItemStatus.COMPLETED:
            action_item.completed_at = None

        await self.db.flush()
        await self.db.refresh(action_item)

        return action_item

    async def delete_action_item(self, action_item_id: int) -> bool:
        """Delete an action item."""
        action_item = await self.get_action_item_or_raise(action_item_id)

        await self.db.delete(action_item)
        await self.db.flush()

        return True

    # ============================================
    # Decision Operations
    # ============================================

    async def list_decisions(self, meeting_id: int) -> list[MeetingDecision]:
        """List all decisions for a meeting."""
        await self.get_meeting_or_raise(meeting_id)

        result = await self.db.execute(
            select(MeetingDecision)
            .where(MeetingDecision.meeting_id == meeting_id)
            .order_by(MeetingDecision.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_result_with_relations(
        self,
        result_id: int,
    ) -> dict:
        """Get result with decisions and action items."""
        meeting_result = await self.get_result_or_raise(result_id)

        decisions = await self.db.execute(
            select(MeetingDecision)
            .where(MeetingDecision.meeting_id == meeting_result.meeting_id)
            .order_by(MeetingDecision.created_at.desc())
        )

        action_items = await self.db.execute(
            select(ActionItem)
            .where(ActionItem.meeting_id == meeting_result.meeting_id)
            .order_by(ActionItem.created_at.desc())
        )

        return {
            "result": meeting_result,
            "decisions": list(decisions.scalars().all()),
            "action_items": list(action_items.scalars().all()),
        }
