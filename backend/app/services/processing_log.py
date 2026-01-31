"""
Processing log service for STT and LLM operations.

Provides async logging functions for monitoring and debugging.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing_log import LLMLog, STTLog

logger = logging.getLogger(__name__)

# Cost estimation constants (Gemini 1.5 Flash pricing per 1M tokens)
GEMINI_INPUT_COST_PER_1M = 0.075  # $0.075 per 1M input tokens
GEMINI_OUTPUT_COST_PER_1M = 0.30  # $0.30 per 1M output tokens


def estimate_cost(
    prompt_tokens: int, completion_tokens: int, provider: str = "gemini"
) -> float:
    """Estimate API cost based on token counts."""
    if provider == "gemini":
        return (prompt_tokens * GEMINI_INPUT_COST_PER_1M / 1_000_000) + (
            completion_tokens * GEMINI_OUTPUT_COST_PER_1M / 1_000_000
        )
    # Add other providers as needed
    return 0.0


class ProcessingLogService:
    """Service for logging STT and LLM processing events."""

    # ==================== STT Logging ====================

    @staticmethod
    async def log_stt_start(
        session: AsyncSession,
        recording_id: int,
        task_id: str | None = None,
        total_chunks: int | None = None,
        audio_duration_seconds: float | None = None,
        audio_file_size_bytes: int | None = None,
    ) -> STTLog:
        """Log STT processing start."""
        log_entry = STTLog(
            recording_id=recording_id,
            task_id=task_id,
            event_type="start",
            total_chunks=total_chunks,
            started_at=datetime.now(timezone.utc),
            audio_duration_seconds=audio_duration_seconds,
            audio_file_size_bytes=audio_file_size_bytes,
        )
        session.add(log_entry)
        await session.commit()
        logger.info(f"STT start logged: recording={recording_id}, chunks={total_chunks}")
        return log_entry

    @staticmethod
    async def log_stt_chunk_complete(
        session: AsyncSession,
        recording_id: int,
        chunk_index: int,
        total_chunks: int,
        duration_seconds: float,
        task_id: str | None = None,
    ) -> STTLog:
        """Log STT chunk processing completion."""
        log_entry = STTLog(
            recording_id=recording_id,
            task_id=task_id,
            event_type="chunk_complete",
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            completed_at=datetime.now(timezone.utc),
            duration_seconds=duration_seconds,
        )
        session.add(log_entry)
        await session.commit()
        logger.debug(f"STT chunk logged: recording={recording_id}, chunk={chunk_index}/{total_chunks}")
        return log_entry

    @staticmethod
    async def log_stt_complete(
        session: AsyncSession,
        recording_id: int,
        task_id: str | None = None,
        duration_seconds: float | None = None,
        transcript_length: int | None = None,
        word_count: int | None = None,
        audio_duration_seconds: float | None = None,
    ) -> STTLog:
        """Log STT processing completion."""
        log_entry = STTLog(
            recording_id=recording_id,
            task_id=task_id,
            event_type="complete",
            completed_at=datetime.now(timezone.utc),
            duration_seconds=duration_seconds,
            transcript_length=transcript_length,
            word_count=word_count,
            audio_duration_seconds=audio_duration_seconds,
        )
        session.add(log_entry)
        await session.commit()
        logger.info(
            f"STT complete logged: recording={recording_id}, "
            f"duration={duration_seconds:.1f}s, words={word_count}"
        )
        return log_entry

    @staticmethod
    async def log_stt_error(
        session: AsyncSession,
        recording_id: int,
        error_type: str,
        error_message: str,
        task_id: str | None = None,
        error_context: dict[str, Any] | None = None,
    ) -> STTLog:
        """Log STT processing error."""
        log_entry = STTLog(
            recording_id=recording_id,
            task_id=task_id,
            event_type="error",
            completed_at=datetime.now(timezone.utc),
            error_type=error_type,
            error_message=error_message,
            error_context=error_context,
        )
        session.add(log_entry)
        await session.commit()
        logger.error(f"STT error logged: recording={recording_id}, type={error_type}, msg={error_message}")
        return log_entry

    # ==================== LLM Logging ====================

    @staticmethod
    async def log_llm_start(
        session: AsyncSession,
        operation: str,
        meeting_id: int | None = None,
        agenda_id: int | None = None,
        task_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        prompt_length: int | None = None,
    ) -> LLMLog:
        """Log LLM API call start."""
        log_entry = LLMLog(
            meeting_id=meeting_id,
            agenda_id=agenda_id,
            task_id=task_id,
            event_type="start",
            operation=operation,
            provider=provider,
            model=model,
            prompt_length=prompt_length,
            started_at=datetime.now(timezone.utc),
        )
        session.add(log_entry)
        await session.commit()
        logger.info(f"LLM start logged: op={operation}, meeting={meeting_id}, provider={provider}")
        return log_entry

    @staticmethod
    async def log_llm_complete(
        session: AsyncSession,
        operation: str,
        meeting_id: int | None = None,
        agenda_id: int | None = None,
        task_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        duration_seconds: float | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        prompt_length: int | None = None,
        response_length: int | None = None,
    ) -> LLMLog:
        """Log LLM API call completion."""
        # Calculate estimated cost
        cost = None
        if prompt_tokens and completion_tokens and provider:
            cost = estimate_cost(prompt_tokens, completion_tokens, provider)

        log_entry = LLMLog(
            meeting_id=meeting_id,
            agenda_id=agenda_id,
            task_id=task_id,
            event_type="complete",
            operation=operation,
            provider=provider,
            model=model,
            completed_at=datetime.now(timezone.utc),
            duration_seconds=duration_seconds,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_length=prompt_length,
            response_length=response_length,
            estimated_cost_usd=cost,
        )
        session.add(log_entry)
        await session.commit()
        logger.info(
            f"LLM complete logged: op={operation}, meeting={meeting_id}, "
            f"duration={duration_seconds:.2f}s, tokens={prompt_tokens}+{completion_tokens}, cost=${cost:.4f}"
        )
        return log_entry

    @staticmethod
    async def log_llm_error(
        session: AsyncSession,
        operation: str,
        error_type: str,
        error_message: str,
        meeting_id: int | None = None,
        agenda_id: int | None = None,
        task_id: str | None = None,
        provider: str | None = None,
        error_context: dict[str, Any] | None = None,
    ) -> LLMLog:
        """Log LLM API call error."""
        log_entry = LLMLog(
            meeting_id=meeting_id,
            agenda_id=agenda_id,
            task_id=task_id,
            event_type="error",
            operation=operation,
            provider=provider,
            completed_at=datetime.now(timezone.utc),
            error_type=error_type,
            error_message=error_message,
            error_context=error_context,
        )
        session.add(log_entry)
        await session.commit()
        logger.error(f"LLM error logged: op={operation}, meeting={meeting_id}, type={error_type}")
        return log_entry
