"""Meeting result API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.schemas.result import (
    ActionItemCreate,
    ActionItemResponse,
    ActionItemUpdate,
    AgendaDiscussionResponse,
    AgendaDiscussionUpdate,
    RegenerateRequest,
    RegenerateResponse,
    ResultCreate,
    ResultDetailResponse,
    ResultResponse,
    ResultUpdate,
    ResultVersionListResponse,
)
from app.services.result import ResultService


router = APIRouter(tags=["results"])


# ============================================
# Meeting Results Endpoints
# ============================================


@router.get("/meetings/{meeting_id}/results", response_model=ResultVersionListResponse)
async def list_results(
    meeting_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get all result versions for a meeting."""
    service = ResultService(db)
    try:
        results = await service.list_results(meeting_id)
        return ResultVersionListResponse(
            data=[ResultResponse.model_validate(r) for r in results],
            meta={"total": len(results)},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/meetings/{meeting_id}/results",
    response_model=ResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_result(
    meeting_id: int,
    data: ResultCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new result version."""
    service = ResultService(db)
    try:
        result = await service.create_result(meeting_id, data)
        return ResultResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================
# Result by ID Endpoints
# ============================================


@router.get("/results/{result_id}", response_model=ResultDetailResponse)
async def get_result(
    result_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a specific result with decisions and action items."""
    service = ResultService(db)
    try:
        data = await service.get_result_with_relations(result_id)
        response = ResultDetailResponse.model_validate(data["result"])
        response.decisions = data["decisions"]
        response.action_items = data["action_items"]
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/results/{result_id}", response_model=ResultResponse)
async def update_result(
    result_id: int,
    data: ResultUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a result (summary, key_points)."""
    service = ResultService(db)
    try:
        result = await service.update_result(result_id, data)
        return ResultResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/results/{result_id}/verify", response_model=ResultResponse)
async def verify_result(
    result_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Mark a result as verified."""
    service = ResultService(db)
    try:
        result = await service.verify_result(result_id)
        return ResultResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/results/{result_id}/regenerate", response_model=RegenerateResponse)
async def regenerate_result(
    result_id: int,
    data: RegenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Trigger LLM regeneration of the meeting result."""
    from workers.tasks.llm import generate_meeting_result

    service = ResultService(db)
    try:
        # Verify result exists
        result = await service.get_result(result_id)

        # Trigger Celery task for LLM regeneration
        task = generate_meeting_result.delay(meeting_id=result.meeting_id)

        return RegenerateResponse(task_id=task.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================
# Action Items Endpoints
# ============================================


@router.get("/meetings/{meeting_id}/action-items", response_model=list[ActionItemResponse])
async def list_action_items(
    meeting_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all action items for a meeting."""
    service = ResultService(db)
    try:
        items = await service.list_action_items(meeting_id)
        return [ActionItemResponse.model_validate(item) for item in items]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/results/{result_id}/action-items",
    response_model=ActionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_action_item(
    result_id: int,
    data: ActionItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Add an action item to a result."""
    service = ResultService(db)
    try:
        # Get the result to find meeting_id
        result = await service.get_result(result_id)
        item = await service.create_action_item(result.meeting_id, data)
        return ActionItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/action-items/{action_item_id}", response_model=ActionItemResponse)
async def update_action_item(
    action_item_id: int,
    data: ActionItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update an action item."""
    service = ResultService(db)
    try:
        item = await service.update_action_item(action_item_id, data)
        return ActionItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/action-items/{action_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_item(
    action_item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete an action item."""
    service = ResultService(db)
    try:
        await service.delete_action_item(action_item_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================
# Agenda Discussions Endpoints
# ============================================


@router.get("/meetings/{meeting_id}/discussions")
async def get_meeting_discussions(
    meeting_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get agenda discussions for a meeting (from latest result)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models import AgendaDiscussion, MeetingResult, Agenda
    from app.services.meeting import MeetingService

    # Verify meeting access
    meeting_service = MeetingService(db)
    await meeting_service.verify_meeting_access(meeting_id)

    # Get latest result
    result = await db.execute(
        select(MeetingResult)
        .where(MeetingResult.meeting_id == meeting_id)
        .order_by(MeetingResult.version.desc())
        .limit(1)
    )
    latest_result = result.scalar_one_or_none()

    if not latest_result:
        return {"data": []}

    # Get all agendas for the meeting to build hierarchy
    from app.models import Meeting
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        return {"data": []}

    # Build agenda hierarchy map (agenda_id -> hierarchical order string)
    all_agendas_result = await db.execute(
        select(Agenda)
        .where(Agenda.meeting_id == meeting_id)
        .order_by(Agenda.parent_id.nullsfirst(), Agenda.order_num)
    )
    all_agendas = list(all_agendas_result.scalars().all())

    # Create a map of agenda_id to its data
    agenda_map = {a.id: a for a in all_agendas}

    # Build hierarchical orders (1-based)
    hierarchical_orders: dict[int, str] = {}
    parent_agendas = [a for a in all_agendas if a.parent_id is None]
    parent_agendas.sort(key=lambda a: a.order_num)

    for idx, parent in enumerate(parent_agendas, 1):
        hierarchical_orders[parent.id] = str(idx)
        children = [a for a in all_agendas if a.parent_id == parent.id]
        children.sort(key=lambda a: a.order_num)
        for i, child in enumerate(children, 1):
            hierarchical_orders[child.id] = f"{idx}.{i}"
            grandchildren = [a for a in all_agendas if a.parent_id == child.id]
            grandchildren.sort(key=lambda a: a.order_num)
            for j, grandchild in enumerate(grandchildren, 1):
                hierarchical_orders[grandchild.id] = f"{idx}.{i}.{j}"

    def get_hierarchical_order(agenda_id: int) -> str:
        """Get hierarchical order string like '1.2.1' (1-based)"""
        return hierarchical_orders.get(agenda_id, "0")

    # Get discussions with agenda info
    discussions_result = await db.execute(
        select(AgendaDiscussion, Agenda)
        .join(Agenda, AgendaDiscussion.agenda_id == Agenda.id)
        .where(AgendaDiscussion.result_id == latest_result.id)
        .order_by(Agenda.level, Agenda.order_num)
    )

    discussions = []
    for disc, agenda in discussions_result:
        hierarchical_order = get_hierarchical_order(agenda.id)
        discussions.append({
            "id": disc.id,
            "agenda_id": disc.agenda_id,
            "agenda_title": agenda.title,
            "agenda_order": hierarchical_order,  # Now hierarchical like "1.2.1"
            "summary": disc.summary,
            "key_points": disc.key_points,
        })

    # Sort by hierarchical order for proper display
    discussions.sort(key=lambda d: [int(x) for x in d["agenda_order"].split(".")])

    return {"data": discussions}


@router.patch("/discussions/{discussion_id}", response_model=AgendaDiscussionResponse)
async def update_discussion(
    discussion_id: int,
    data: AgendaDiscussionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update an agenda discussion."""
    from sqlalchemy import select
    from app.models import AgendaDiscussion, MeetingResult
    from app.services.meeting import MeetingService

    # Get the discussion
    result = await db.execute(
        select(AgendaDiscussion).where(AgendaDiscussion.id == discussion_id)
    )
    discussion = result.scalar_one_or_none()

    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )

    # Verify access via result -> meeting
    result_obj = await db.execute(
        select(MeetingResult).where(MeetingResult.id == discussion.result_id)
    )
    meeting_result = result_obj.scalar_one_or_none()
    if meeting_result:
        meeting_service = MeetingService(db)
        await meeting_service.verify_meeting_access(meeting_result.meeting_id)

    # Update fields
    if data.summary is not None:
        discussion.summary = data.summary
    if data.key_points is not None:
        discussion.key_points = data.key_points

    await db.commit()
    await db.refresh(discussion)

    return AgendaDiscussionResponse.model_validate(discussion)


@router.delete("/discussions/{discussion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discussion(
    discussion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete an agenda discussion."""
    from sqlalchemy import select
    from app.models import AgendaDiscussion, MeetingResult
    from app.services.meeting import MeetingService

    # Get the discussion
    result = await db.execute(
        select(AgendaDiscussion).where(AgendaDiscussion.id == discussion_id)
    )
    discussion = result.scalar_one_or_none()

    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )

    # Verify access via result -> meeting
    result_obj = await db.execute(
        select(MeetingResult).where(MeetingResult.id == discussion.result_id)
    )
    meeting_result = result_obj.scalar_one_or_none()
    if meeting_result:
        meeting_service = MeetingService(db)
        await meeting_service.verify_meeting_access(meeting_result.meeting_id)

    # Delete
    await db.delete(discussion)
    await db.commit()
