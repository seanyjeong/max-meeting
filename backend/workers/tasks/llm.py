"""
LLM Celery tasks for generating meeting summaries and questions.

Handles AI-powered meeting result generation.
Based on spec Section 5 (Phase 5: Meeting Results) and Section 9 (LLM Prompts).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import redis
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_redis_client() -> redis.Redis:
    """Get a Redis client for progress updates."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_progress(
    meeting_id: int,
    progress: int,
    status: str,
    message: str = "",
) -> None:
    """Publish progress update via Redis Pub/Sub."""
    try:
        r = get_redis_client()
        channel = f"llm:progress:{meeting_id}"
        data = {
            "meeting_id": meeting_id,
            "progress": progress,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.publish(channel, str(data))

        # Also store the last status for SSE reconnection
        r.setex(f"llm:last_status:{meeting_id}", 3600, str(data))

    except Exception as e:
        logger.warning(f"Failed to publish progress: {e}")


@shared_task(
    bind=True,
    name="workers.tasks.llm.generate_meeting_result",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=300,  # 5 minutes
    time_limit=360,
)
def generate_meeting_result(
    self,
    meeting_id: int,
) -> dict[str, Any]:
    """
    Generate meeting result using LLM.

    Gathers all transcripts, notes, and sketches for the meeting,
    then uses LLM to generate a summary, discussions, decisions,
    and action items.

    Args:
        meeting_id: ID of the meeting to process

    Returns:
        Dict with generated result IDs and content summary
    """
    logger.info(f"Starting LLM result generation for meeting {meeting_id}")

    async def _generate():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy.orm import selectinload

        from app.models import (
            ActionItem,
            ActionItemPriority,
            ActionItemStatus,
            Agenda,
            AgendaDiscussion,
            DecisionType,
            Meeting,
            MeetingDecision,
            MeetingResult,
            TaskStatusEnum,
            TaskTracking,
        )
        from app.services.llm import get_llm_service

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Create task tracking (meeting_id stored in result field since column doesn't exist)
            task = TaskTracking(
                task_id=self.request.id,
                task_type="llm_result",
                status=TaskStatusEnum.PROCESSING,
                started_at=datetime.now(timezone.utc),
                result={"meeting_id": meeting_id},  # Store meeting_id in result JSON
            )
            session.add(task)
            await session.commit()

            publish_progress(
                meeting_id=meeting_id,
                progress=5,
                status="processing",
                message="Gathering meeting data",
            )

            # Load meeting with all related data
            result = await session.execute(
                select(Meeting)
                .options(
                    selectinload(Meeting.agendas).selectinload(Agenda.questions),
                    selectinload(Meeting.attendees),
                    selectinload(Meeting.transcripts),
                    selectinload(Meeting.manual_notes),
                    selectinload(Meeting.sketches),
                )
                .where(Meeting.id == meeting_id)
            )
            meeting = result.scalar_one_or_none()

            if not meeting:
                raise ValueError(f"Meeting {meeting_id} not found")

            publish_progress(
                meeting_id=meeting_id,
                progress=15,
                status="processing",
                message="Preparing transcript data",
            )

            # Gather ALL transcript segments with timestamps
            all_segments = []
            for transcript in meeting.transcripts:
                if transcript.segments:
                    for segment in transcript.segments:
                        all_segments.append({
                            "start": segment.get("start", 0),
                            "end": segment.get("end", 0),
                            "text": segment.get("text", ""),
                            "speaker": segment.get("speaker"),
                        })

            # Sort segments by start time
            all_segments.sort(key=lambda x: x["start"])

            # Build full transcript for overall summary
            full_transcript = " ".join(seg["text"] for seg in all_segments if seg["text"])

            if not full_transcript:
                logger.warning(f"No transcript text found for meeting {meeting_id}")

            # Build per-agenda transcript based on time_segments (or fallback to started_at_seconds)
            agenda_transcripts = {}  # agenda_id -> transcript text

            def get_agenda_transcript(agenda, all_segs: list[dict]) -> str:
                """Extract transcript for an agenda from its time segments.

                Uses segment midpoint for matching to handle cases where user
                clicks agenda slightly after starting to speak.
                """
                # Priority 1: Use time_segments if available (supports multiple segments)
                if agenda.time_segments:
                    texts = []
                    for seg in agenda.time_segments:
                        start = seg.get('start', 0)
                        end = seg.get('end') or float('inf')
                        matching = [
                            s["text"] for s in all_segs
                            if s["text"] and start <= (s["start"] + s.get("end", s["start"])) / 2 < end
                        ]
                        texts.extend(matching)
                    return " ".join(texts)

                # Priority 2: Fallback to started_at_seconds (legacy single timestamp)
                elif agenda.started_at_seconds is not None:
                    # Find next agenda's start time for end boundary
                    agendas_sorted = sorted(
                        [a for a in meeting.agendas if a.started_at_seconds is not None],
                        key=lambda a: a.started_at_seconds
                    )
                    idx = next((i for i, a in enumerate(agendas_sorted) if a.id == agenda.id), -1)
                    start_time = agenda.started_at_seconds
                    if idx >= 0 and idx + 1 < len(agendas_sorted):
                        end_time = agendas_sorted[idx + 1].started_at_seconds
                    else:
                        end_time = float('inf')

                    matching = [
                        s["text"] for s in all_segs
                        if s["text"] and start_time <= (s["start"] + s.get("end", s["start"])) / 2 < end_time
                    ]
                    return " ".join(matching)

                return ""

            # Process all agendas
            for agenda in meeting.agendas:
                transcript_text = get_agenda_transcript(agenda, all_segments)
                agenda_transcripts[agenda.id] = transcript_text

                # Log info
                if agenda.time_segments:
                    seg_count = len(agenda.time_segments)
                    total_duration = sum(
                        (seg.get('end') or 0) - seg.get('start', 0)
                        for seg in agenda.time_segments
                        if seg.get('end')
                    )
                    logger.info(f"Agenda '{agenda.title}' ({seg_count} segments, ~{total_duration}s): {len(transcript_text.split())} words")
                elif agenda.started_at_seconds is not None:
                    logger.info(f"Agenda '{agenda.title}' (legacy @{agenda.started_at_seconds}s): {len(transcript_text.split())} words")
                else:
                    logger.info(f"Agenda '{agenda.title}' (no timestamp): LLM will auto-classify")

            # Gather manual notes
            notes_texts = [note.content for note in meeting.manual_notes if note.content]
            notes_combined = "\n".join(notes_texts) if notes_texts else None

            # Gather sketch texts
            sketch_texts = [
                sketch.extracted_text
                for sketch in meeting.sketches
                if sketch.extracted_text
            ]
            sketches_combined = "\n".join(sketch_texts) if sketch_texts else None

            # Prepare agenda info with per-agenda transcripts
            # Sort agendas: parents first (by order_num), then children (by parent_id, order_num)
            parent_agendas = [a for a in meeting.agendas if a.parent_id is None]
            parent_agendas.sort(key=lambda a: a.order_num)

            # Build child_order map for each parent (supports 3 levels)
            child_orders: dict[int, int] = {}  # agenda_id -> child_order (1-based)
            hierarchical_orders: dict[int, str] = {}  # agenda_id -> hierarchical order string (e.g., "1.2.1")

            for parent in parent_agendas:
                hierarchical_orders[parent.id] = str(parent.order_num)
                children = [a for a in meeting.agendas if a.parent_id == parent.id]
                children.sort(key=lambda a: a.order_num)
                for i, child in enumerate(children, 1):
                    child_orders[child.id] = i
                    hierarchical_orders[child.id] = f"{parent.order_num}.{i}"
                    # 3레벨 손자안건 처리
                    grandchildren = [a for a in meeting.agendas if a.parent_id == child.id]
                    grandchildren.sort(key=lambda a: a.order_num)
                    for j, grandchild in enumerate(grandchildren, 1):
                        child_orders[grandchild.id] = j
                        hierarchical_orders[grandchild.id] = f"{parent.order_num}.{i}.{j}"

            agenda_info = [
                {
                    "id": agenda.id,
                    "title": agenda.title,
                    "order": agenda.order_num,
                    "parent_id": agenda.parent_id,
                    "level": agenda.level,
                    "child_order": child_orders.get(agenda.id, agenda.order_num),
                    "hierarchical_order": hierarchical_orders.get(agenda.id, str(agenda.order_num)),
                    "transcript": agenda_transcripts.get(agenda.id, ""),
                }
                for agenda in meeting.agendas
            ]
            agenda_titles = [agenda.title for agenda in meeting.agendas]

            # Prepare meeting info
            attendee_names = []
            for attendee in meeting.attendees:
                if attendee.contact:
                    attendee_names.append(attendee.contact.name)

            meeting_info = {
                "title": meeting.title,
                "scheduled_at": meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
                "attendees": attendee_names,
                "agenda_info": agenda_info,  # Include per-agenda transcript info
            }

            publish_progress(
                meeting_id=meeting_id,
                progress=30,
                status="generating",
                message="Generating meeting summary with AI",
            )

            # Call LLM service
            llm_service = get_llm_service()
            llm_result = await llm_service.generate_meeting_summary(
                transcript=full_transcript,
                agenda_titles=agenda_titles,
                meeting_info=meeting_info,
                notes=notes_combined,
                sketch_texts=sketches_combined,
            )

            publish_progress(
                meeting_id=meeting_id,
                progress=70,
                status="saving",
                message="Saving results to database",
            )

            # Get the latest version number
            version_result = await session.execute(
                select(MeetingResult)
                .where(MeetingResult.meeting_id == meeting_id)
                .order_by(MeetingResult.version.desc())
                .limit(1)
            )
            latest_result = version_result.scalar_one_or_none()
            new_version = (latest_result.version + 1) if latest_result else 1

            # Create meeting result
            meeting_result = MeetingResult(
                meeting_id=meeting_id,
                summary=llm_result["summary"],
                version=new_version,
            )
            session.add(meeting_result)

            # Flush to get meeting_result.id
            await session.flush()

            # Build agenda_id lookup set for validation
            valid_agenda_ids = {a.id for a in meeting.agendas}

            # Create agenda discussions
            for discussion in llm_result["discussions"]:
                # Prefer agenda_id (direct), fallback to agenda_idx (index-based)
                agenda_id = discussion.get("agenda_id")
                if agenda_id is None:
                    agenda_idx = discussion.get("agenda_idx", 0)
                    agenda_id = meeting.agendas[agenda_idx].id if agenda_idx < len(meeting.agendas) else None

                if agenda_id and agenda_id in valid_agenda_ids:
                    agenda_disc = AgendaDiscussion(
                        result_id=meeting_result.id,
                        agenda_id=agenda_id,
                        summary=discussion["content"],  # DB uses 'summary' not 'content'
                    )
                    session.add(agenda_disc)

            # Create decisions
            for decision in llm_result["decisions"]:
                # Prefer agenda_id (direct), fallback to agenda_idx (index-based)
                agenda_id = decision.get("agenda_id")
                if agenda_id is None:
                    agenda_idx = decision.get("agenda_idx", 0)
                    agenda_id = meeting.agendas[agenda_idx].id if agenda_idx < len(meeting.agendas) else None

                decision_type = decision.get("type", "approved")
                try:
                    decision_enum = DecisionType(decision_type)
                except ValueError:
                    decision_enum = DecisionType.APPROVED

                meeting_decision = MeetingDecision(
                    result_id=meeting_result.id,  # DB uses result_id not meeting_id
                    agenda_id=agenda_id,
                    content=decision["content"],
                    decision_type=decision_enum,
                )
                session.add(meeting_decision)

            # Create action items
            for item in llm_result["action_items"]:
                # Prefer agenda_id (direct), fallback to agenda_idx (index-based)
                agenda_id = item.get("agenda_id")
                if agenda_id is None:
                    agenda_idx = item.get("agenda_idx", 0)
                    agenda_id = meeting.agendas[agenda_idx].id if agenda_idx < len(meeting.agendas) else None

                # Parse due date if provided
                due_date = None
                if item.get("due_date"):
                    try:
                        from datetime import date
                        due_date = date.fromisoformat(item["due_date"])
                    except (ValueError, TypeError):
                        pass

                # title is required, use content if not provided
                title = item.get("title") or item["content"][:200]

                action_item = ActionItem(
                    meeting_id=meeting_id,
                    agenda_id=agenda_id,
                    title=title,
                    content=item["content"],
                    due_date=due_date,
                    priority=ActionItemPriority.MEDIUM,
                    status=ActionItemStatus.PENDING,
                )
                session.add(action_item)

            # Update task tracking
            task.status = TaskStatusEnum.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.progress = 100
            task.result = {
                "version": new_version,
                "num_discussions": len(llm_result["discussions"]),
                "num_decisions": len(llm_result["decisions"]),
                "num_action_items": len(llm_result["action_items"]),
            }

            await session.commit()
            await session.refresh(meeting_result)

            publish_progress(
                meeting_id=meeting_id,
                progress=100,
                status="completed",
                message="Meeting result generated successfully",
            )

            return {
                "meeting_id": meeting_id,
                "result_id": meeting_result.id,
                "version": new_version,
                "summary_preview": llm_result["summary"][:200] + "..."
                if len(llm_result["summary"]) > 200
                else llm_result["summary"],
                "num_discussions": len(llm_result["discussions"]),
                "num_decisions": len(llm_result["decisions"]),
                "num_action_items": len(llm_result["action_items"]),
                "status": "completed",
            }

    try:
        return asyncio.run(_generate())

    except SoftTimeLimitExceeded:
        logger.error(f"LLM generation timed out for meeting {meeting_id}")
        publish_progress(
            meeting_id=meeting_id,
            progress=0,
            status="failed",
            message="Generation timed out",
        )
        raise

    except Exception as e:
        logger.error(f"LLM generation failed for meeting {meeting_id}: {e}")
        publish_progress(
            meeting_id=meeting_id,
            progress=0,
            status="failed",
            message=str(e),
        )
        raise


@shared_task(
    bind=True,
    name="workers.tasks.llm.generate_questions",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    soft_time_limit=60,
    time_limit=90,
)
def generate_questions(
    self,
    agenda_id: int,
    num_questions: int = 4,
) -> dict[str, Any]:
    """
    Generate discussion questions for an agenda item.

    Args:
        agenda_id: ID of the agenda item
        num_questions: Number of questions to generate

    Returns:
        Dict with generated question IDs and content
    """
    logger.info(f"Generating questions for agenda {agenda_id}")

    async def _generate():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from app.models import Agenda, AgendaQuestion
        from app.services.llm import get_llm_service

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Get agenda
            result = await session.execute(
                select(Agenda).where(Agenda.id == agenda_id)
            )
            agenda = result.scalar_one_or_none()

            if not agenda:
                raise ValueError(f"Agenda {agenda_id} not found")

            # Generate questions using LLM
            llm_service = get_llm_service()
            questions = await llm_service.generate_questions(
                agenda_title=agenda.title,
                agenda_description=agenda.description,
                num_questions=num_questions,
            )

            # Delete existing generated questions
            existing = await session.execute(
                select(AgendaQuestion)
                .where(AgendaQuestion.agenda_id == agenda_id)
                .where(AgendaQuestion.is_generated == True)  # noqa: E712
            )
            for q in existing.scalars().all():
                await session.delete(q)

            # Create new questions
            created_ids = []
            for i, question_text in enumerate(questions):
                question = AgendaQuestion(
                    agenda_id=agenda_id,
                    question=question_text,
                    order_num=i,
                    is_generated=True,
                    answered=False,
                )
                session.add(question)
                await session.flush()
                created_ids.append(question.id)

            await session.commit()

            return {
                "agenda_id": agenda_id,
                "questions": questions,
                "question_ids": created_ids,
                "num_questions": len(questions),
                "status": "completed",
            }

    try:
        return asyncio.run(_generate())

    except Exception as e:
        logger.error(f"Question generation failed for agenda {agenda_id}: {e}")
        raise


@shared_task(
    bind=True,
    name="workers.tasks.llm.regenerate_meeting_result",
    acks_late=True,
)
def regenerate_meeting_result(
    self,
    meeting_id: int,
) -> dict[str, Any]:
    """
    Regenerate meeting result (creates a new version).

    Args:
        meeting_id: ID of the meeting

    Returns:
        Dict with new result info
    """
    logger.info(f"Regenerating result for meeting {meeting_id}")

    # Simply trigger a new generation (it will create a new version)
    return generate_meeting_result.delay(meeting_id).id
