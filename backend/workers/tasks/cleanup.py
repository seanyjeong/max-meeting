"""
Cleanup tasks for removing old recording files.

Recordings are deleted 3 days after meeting result (LLM analysis) is generated.
"""

import os
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="workers.tasks.cleanup.cleanup_old_recordings",
    acks_late=True,
)
def cleanup_old_recordings(retention_days: int = 3) -> dict:
    """
    Delete recording files that are older than retention_days after LLM result generation.

    Args:
        retention_days: Days to keep recordings after meeting result is created (default: 3)

    Returns:
        Dict with cleanup statistics
    """
    import asyncio
    from sqlalchemy import select, and_
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models import Recording, RecordingStatus
    from app.models.meeting_result import MeetingResult

    settings = get_settings()

    async def _cleanup():
        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        deleted_count = 0
        deleted_size = 0
        errors = []

        async with async_session() as session:
            # Find recordings where:
            # 1. Meeting has a result (LLM analysis done)
            # 2. Result was created more than retention_days ago
            # 3. Recording file still exists
            result = await session.execute(
                select(Recording, MeetingResult)
                .join(MeetingResult, Recording.meeting_id == MeetingResult.meeting_id)
                .where(
                    and_(
                        MeetingResult.created_at < cutoff_date,
                        Recording.file_path.isnot(None),
                        Recording.status == RecordingStatus.COMPLETED,
                    )
                )
            )

            rows = result.all()

            for recording, meeting_result in rows:
                file_path = recording.file_path

                if not file_path or not os.path.exists(file_path):
                    continue

                try:
                    # Get file size before deletion
                    file_size = os.path.getsize(file_path)

                    # Delete the file
                    os.remove(file_path)

                    # Try to remove empty parent directory
                    parent_dir = os.path.dirname(file_path)
                    if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                        os.rmdir(parent_dir)

                    # Update recording record
                    recording.file_path = None

                    deleted_count += 1
                    deleted_size += file_size

                    logger.info(
                        f"Deleted recording file: {file_path} "
                        f"(meeting_id={recording.meeting_id}, size={file_size/1024/1024:.1f}MB)"
                    )

                except Exception as e:
                    error_msg = f"Failed to delete {file_path}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            await session.commit()

        await engine.dispose()

        return {
            "deleted_count": deleted_count,
            "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
            "errors": errors,
            "retention_days": retention_days,
        }

    result = asyncio.run(_cleanup())

    logger.info(
        f"Cleanup complete: {result['deleted_count']} files deleted, "
        f"{result['deleted_size_mb']}MB freed"
    )

    return result
