"""Agenda API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import AgendaQuestion
from app.schemas.agenda import (
    AgendaCreate,
    AgendaListResponse,
    AgendaMoveRequest,
    AgendaMoveResponse,
    AgendaParsePreviewResponse,
    AgendaParseRequest,
    AgendaParseResponse,
    AgendaResponse,
    AgendaUpdate,
    ParsedAgendaItem,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    ReorderRequest,
    ReorderResponse,
)
from app.services.agenda import AgendaService
from app.services.llm import get_llm_service, generate_questions

logger = logging.getLogger(__name__)


router = APIRouter(tags=["agendas"])


# ============================================
# Meeting Agenda Endpoints
# ============================================


@router.get("/meetings/{meeting_id}/agendas", response_model=AgendaListResponse)
async def list_agendas(
    meeting_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    tree: bool = True,
):
    """
    List all agendas for a meeting with their questions.

    Args:
        tree: If true (default), returns hierarchical structure with children.
              If false, returns flat list.
    """
    service = AgendaService(db)
    try:
        if tree:
            agendas = await service.list_agendas_tree(meeting_id)
        else:
            agendas = await service.list_agendas(meeting_id)

        def convert_agenda(agenda) -> AgendaResponse:
            """Convert agenda with children recursively."""
            response = AgendaResponse.model_validate(agenda)
            if hasattr(agenda, 'children') and agenda.children:
                response.children = [convert_agenda(c) for c in agenda.children]
            return response

        data = [convert_agenda(a) for a in agendas]
        return AgendaListResponse(
            data=data,
            meta={"total": len(agendas), "tree": tree},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/meetings/{meeting_id}/agendas",
    response_model=AgendaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agenda(
    meeting_id: int,
    data: AgendaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new agenda for a meeting."""
    service = AgendaService(db)
    try:
        agenda = await service.create_agenda(meeting_id, data)

        # Auto-generate questions using Gemini
        try:
            questions_text = await generate_questions(
                agenda_title=agenda.title,
                agenda_description=agenda.description,
                num_questions=4,
            )

            for i, q in enumerate(questions_text):
                question = AgendaQuestion(
                    agenda_id=agenda.id,
                    question=q,
                    order_num=i,
                    is_generated=True,
                    answered=False,
                )
                db.add(question)

            await db.commit()
            await db.refresh(agenda)

        except Exception as e:
            logger.warning(f"Failed to auto-generate questions for agenda {agenda.id}: {e}")
            # Question generation failure should not block agenda creation
            await db.commit()

        return AgendaResponse.model_validate(agenda)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/meetings/{meeting_id}/agendas/parse",
    response_model=AgendaParseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def parse_agenda_text(
    meeting_id: int,
    body: AgendaParseRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Parse raw text to create multiple agendas with hierarchical structure.

    This endpoint uses Gemini AI to extract structured agenda items
    from unstructured text. Sub-items are created as child agendas.
    Questions are only auto-generated for root-level agendas.
    """
    agenda_service = AgendaService(db)
    llm_service = get_llm_service()

    async def create_agenda_recursive(
        item: dict,
        parent_id: int | None = None,
        is_root: bool = True
    ) -> AgendaResponse:
        """Recursively create agenda and its children."""
        agenda_data = AgendaCreate(
            title=item["title"],
            description=item.get("description"),
            parent_id=parent_id,
        )
        agenda = await agenda_service.create_agenda(meeting_id, agenda_data)

        # Auto-generate questions only for root-level agendas
        if is_root:
            try:
                questions_text = await generate_questions(
                    agenda_title=agenda.title,
                    agenda_description=agenda.description,
                    num_questions=4,
                )

                for i, q in enumerate(questions_text):
                    question = AgendaQuestion(
                        agenda_id=agenda.id,
                        question=q,
                        order_num=i,
                        is_generated=True,
                        answered=False,
                    )
                    db.add(question)

                await db.flush()

            except Exception as e:
                logger.warning(f"Failed to auto-generate questions for agenda {agenda.id}: {e}")

        # Create children recursively
        children_responses = []
        for child_item in item.get("children", []):
            child_response = await create_agenda_recursive(
                child_item,
                parent_id=agenda.id,
                is_root=False
            )
            children_responses.append(child_response)

        # Build response with children
        response = AgendaResponse.model_validate(agenda)
        response.children = children_responses
        return response

    try:
        # First verify the meeting exists
        meeting = await agenda_service.get_meeting_or_raise(meeting_id)

        # Parse the text using LLM (now returns hierarchical structure)
        parsed_items = await llm_service.parse_agenda_text(
            raw_text=body.text,
            meeting_title=meeting.title,
        )

        # Create agenda items with hierarchy
        created_agendas = []
        for item in parsed_items:
            agenda_response = await create_agenda_recursive(item)
            created_agendas.append(agenda_response)

        await db.commit()

        # Count total agendas (including children)
        def count_total(items: list) -> int:
            total = len(items)
            for item in items:
                if hasattr(item, 'children'):
                    total += count_total(item.children)
            return total

        return AgendaParseResponse(
            data=created_agendas,
            meta={
                "total": count_total(created_agendas),
                "root_count": len(created_agendas),
                "source": "llm_parsed",
                "hierarchical": True,
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse agenda text: {str(e)}",
        )


# ============================================
# Parse Preview Endpoint (no meeting_id required)
# ============================================


@router.post(
    "/agendas/parse-preview",
    response_model=AgendaParsePreviewResponse,
)
async def parse_agenda_preview(
    body: AgendaParseRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Parse raw text to preview agenda items without saving.

    This endpoint uses Gemini AI to extract structured agenda items
    from unstructured text with hierarchical structure.
    Unlike /meetings/{id}/agendas/parse, this does NOT save anything
    to the database - it's for preview before creating a meeting.
    """
    llm_service = get_llm_service()

    def convert_to_preview(item: dict) -> ParsedAgendaItem:
        """Recursively convert parsed item to preview format."""
        children = [
            convert_to_preview(child)
            for child in item.get("children", [])
        ]
        return ParsedAgendaItem(
            title=item["title"],
            description=item.get("description"),
            children=children,
        )

    try:
        # Parse the text using LLM (returns hierarchical structure)
        parsed_items = await llm_service.parse_agenda_text(
            raw_text=body.text,
            meeting_title=None,  # No meeting context for preview
        )

        # Convert to preview response format with hierarchy
        items = [convert_to_preview(item) for item in parsed_items]

        # Count total including children
        def count_total(items_list: list) -> int:
            total = len(items_list)
            for item in items_list:
                total += count_total(item.children)
            return total

        return AgendaParsePreviewResponse(
            items=items,
            meta={
                "total": count_total(items),
                "root_count": len(items),
                "source": "llm_parsed",
                "hierarchical": True,
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse agenda text: {str(e)}",
        )


# ============================================
# Agenda Endpoints (by ID)
# ============================================


@router.get("/agendas/{agenda_id}", response_model=AgendaResponse)
async def get_agenda(
    agenda_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a specific agenda by ID."""
    service = AgendaService(db)
    try:
        agenda = await service.get_agenda_or_raise(agenda_id)
        return AgendaResponse.model_validate(agenda)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/agendas/{agenda_id}", response_model=AgendaResponse)
async def update_agenda(
    agenda_id: int,
    data: AgendaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update an agenda (title, description, order, status)."""
    service = AgendaService(db)
    try:
        agenda = await service.update_agenda(agenda_id, data)
        return AgendaResponse.model_validate(agenda)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/agendas/{agenda_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agenda(
    agenda_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete an agenda (soft delete)."""
    service = AgendaService(db)
    try:
        await service.delete_agenda(agenda_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/agendas/{agenda_id}/reorder", response_model=ReorderResponse)
async def reorder_agendas(
    agenda_id: int,
    data: ReorderRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Reorder agendas (for drag-drop support)."""
    service = AgendaService(db)
    try:
        # First get the agenda to find its meeting_id
        agenda = await service.get_agenda_or_raise(agenda_id)
        updated_count = await service.reorder_agendas(agenda.meeting_id, data.items)
        return ReorderResponse(success=True, updated_count=updated_count)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/agendas/{agenda_id}/move", response_model=AgendaMoveResponse)
async def move_agenda(
    agenda_id: int,
    data: AgendaMoveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Move an agenda to a new parent and/or position in the hierarchy.

    This endpoint handles:
    - Moving to a different parent (nesting)
    - Moving to root level (set new_parent_id to null)
    - Reordering within the same parent level

    Validation:
    - Cannot move an agenda to its own descendant
    - Parent must belong to the same meeting
    """
    service = AgendaService(db)
    try:
        agenda = await service.move_agenda(agenda_id, data)
        await db.commit()
        return AgendaMoveResponse(
            success=True,
            agenda=AgendaResponse.model_validate(agenda),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================
# Question Endpoints
# ============================================


@router.post(
    "/agendas/{agenda_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    agenda_id: int,
    data: QuestionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Add a question to an agenda."""
    service = AgendaService(db)
    try:
        question = await service.add_question(agenda_id, data)
        return QuestionResponse.model_validate(question)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    data: QuestionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a question."""
    service = AgendaService(db)
    try:
        question = await service.update_question(question_id, data)
        return QuestionResponse.model_validate(question)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a question."""
    service = AgendaService(db)
    try:
        await service.delete_question(question_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
