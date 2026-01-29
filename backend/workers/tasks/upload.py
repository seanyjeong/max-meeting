"""
Upload-related Celery tasks.

Handles post-upload processing and file finalization.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

from celery import shared_task

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def compute_file_checksum(file_path: str) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def get_audio_duration(file_path: str) -> int | None:
    """Get audio duration in seconds using ffprobe."""
    import subprocess

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return int(float(result.stdout.strip()))
        return None

    except Exception as e:
        logger.warning(f"Failed to get audio duration: {e}")
        return None


@shared_task(
    bind=True,
    name="workers.tasks.upload.finalize_upload",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def finalize_upload(
    self,
    recording_id: int,
    file_path: str,
    trigger_stt: bool = True,
) -> dict[str, Any]:
    """
    Finalize an uploaded recording file.

    Verifies the file, computes checksum, updates metadata,
    and optionally triggers STT processing.

    Args:
        recording_id: ID of the recording record
        file_path: Path to the uploaded file
        trigger_stt: Whether to automatically trigger STT processing

    Returns:
        Dict with finalization results
    """
    import asyncio

    logger.info(f"Finalizing upload for recording {recording_id}")

    async def _finalize():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from app.models import Recording, RecordingStatus

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Get recording
            result = await session.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = result.scalar_one_or_none()

            if not recording:
                raise ValueError(f"Recording {recording_id} not found")

            # Verify file exists
            if not os.path.exists(file_path):
                recording.status = RecordingStatus.FAILED
                recording.error_message = "File not found after upload"
                await session.commit()
                raise FileNotFoundError(f"Uploaded file not found: {file_path}")

            # Compute checksum
            checksum = compute_file_checksum(file_path)

            # Get file size
            file_size = os.path.getsize(file_path)

            # Get audio duration
            duration = get_audio_duration(file_path)

            # Update recording
            recording.checksum = checksum
            recording.file_size_bytes = file_size
            recording.duration_seconds = duration
            recording.status = RecordingStatus.UPLOADED

            await session.commit()

            return {
                "recording_id": recording_id,
                "checksum": checksum,
                "file_size_bytes": file_size,
                "duration_seconds": duration,
                "status": "uploaded",
            }

    try:
        result = asyncio.get_event_loop().run_until_complete(_finalize())

        # Trigger STT processing if requested
        if trigger_stt:
            from workers.tasks.stt import process_recording
            stt_task_id = process_recording.delay(recording_id).id
            result["stt_task_id"] = stt_task_id
            logger.info(f"Triggered STT task {stt_task_id} for recording {recording_id}")

        return result

    except Exception as e:
        logger.error(f"Upload finalization failed for recording {recording_id}: {e}")
        raise


@shared_task(
    bind=True,
    name="workers.tasks.upload.verify_upload_integrity",
    acks_late=True,
)
def verify_upload_integrity(
    self,
    recording_id: int,
    expected_checksum: str | None = None,
) -> dict[str, Any]:
    """
    Verify the integrity of an uploaded file.

    Args:
        recording_id: ID of the recording
        expected_checksum: Optional expected checksum to verify against

    Returns:
        Dict with verification result
    """
    import asyncio

    async def _verify():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from app.models import Recording

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = result.scalar_one_or_none()

            if not recording:
                return {"valid": False, "error": "Recording not found"}

            if not os.path.exists(recording.file_path):
                return {"valid": False, "error": "File not found"}

            current_checksum = compute_file_checksum(recording.file_path)

            # Verify against stored checksum
            stored_valid = current_checksum == recording.checksum

            # Verify against expected checksum if provided
            expected_valid = True
            if expected_checksum:
                expected_valid = current_checksum == expected_checksum

            return {
                "recording_id": recording_id,
                "valid": stored_valid and expected_valid,
                "current_checksum": current_checksum,
                "stored_checksum": recording.checksum,
                "checksums_match": stored_valid,
            }

    return asyncio.get_event_loop().run_until_complete(_verify())


@shared_task(
    bind=True,
    name="workers.tasks.upload.cleanup_failed_uploads",
    acks_late=True,
)
def cleanup_failed_uploads(
    self,
    max_age_hours: int = 24,
) -> dict[str, Any]:
    """
    Clean up failed or orphaned upload files.

    Args:
        max_age_hours: Maximum age in hours for failed uploads

    Returns:
        Dict with cleanup results
    """
    import asyncio
    from datetime import timedelta

    async def _cleanup():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from app.models import Recording, RecordingStatus

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        deleted_files = 0
        deleted_records = 0

        async with async_session() as session:
            # Find old failed recordings
            result = await session.execute(
                select(Recording)
                .where(Recording.status == RecordingStatus.FAILED)
                .where(Recording.created_at < cutoff_time)
            )
            failed_recordings = result.scalars().all()

            for recording in failed_recordings:
                # Delete file if exists
                if recording.file_path and os.path.exists(recording.file_path):
                    try:
                        os.remove(recording.file_path)
                        deleted_files += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete file {recording.file_path}: {e}")

                # Delete record
                await session.delete(recording)
                deleted_records += 1

            await session.commit()

            return {
                "deleted_files": deleted_files,
                "deleted_records": deleted_records,
                "cutoff_time": cutoff_time.isoformat(),
            }

    return asyncio.get_event_loop().run_until_complete(_cleanup())
