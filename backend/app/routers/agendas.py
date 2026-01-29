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
):
    """List all agendas for a meeting with their questions."""
    service = AgendaService(db)
    try:
        agendas = await service.list_agendas(meeting_id)
        return AgendaListResponse(
            data=[AgendaResponse.model_validate(a) for a in agendas],
            meta={"total": len(agendas)},
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
    Parse raw text to create multiple agendas.

    This endpoint uses Gemini AI to extract structured agenda items
    from unstructured text (e.g., pasted from notes, emails, etc).
    """
    agenda_service = AgendaService(db)
    llm_service = get_llm_service()

    try:
        # First verify the meeting exists (using AgendaService which has the method)
        meeting = await agenda_service.get_meeting_or_raise(meeting_id)

        # Parse the text using LLM
        parsed_items = await llm_service.parse_agenda_text(
            raw_text=body.text,
            meeting_title=meeting.title,
        )

        # Create agenda items in the database
        created_agendas = []
        for item in parsed_items:
            agenda_data = AgendaCreate(
                title=item["title"],
                description=item["description"] if item["description"] else None,
            )
            agenda = await agenda_service.create_agenda(meeting_id, agenda_data)

            # Auto-generate questions for each parsed agenda
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

            created_agendas.append(AgendaResponse.model_validate(agenda))

        return AgendaParseResponse(
            data=created_agendas,
            meta={"total": len(created_agendas), "source": "llm_parsed"},
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
    from unstructured text. Unlike /meetings/{id}/agendas/parse,
    this does NOT save anything to the database - it's for preview
    before creating a meeting.
    """
    llm_service = get_llm_service()

    try:
        # Parse the text using LLM
        parsed_items = await llm_service.parse_agenda_text(
            raw_text=body.text,
            meeting_title=None,  # No meeting context for preview
        )

        # Convert to preview response format
        items = [
            ParsedAgendaItem(
                title=item["title"],
                description=item.get("description"),
            )
            for item in parsed_items
        ]

        return AgendaParsePreviewResponse(
            items=items,
            meta={"total": len(items), "source": "llm_parsed"},
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
