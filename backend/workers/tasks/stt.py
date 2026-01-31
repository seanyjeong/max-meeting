"""
STT Celery tasks for processing audio recordings.

Handles audio transcription with chunk-based parallel processing.
Based on spec Section 4 (Phase 4: STT + upload).
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any

import redis
from celery import chain, chord, shared_task
from celery.exceptions import SoftTimeLimitExceeded

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Processing Log Helpers ====================

def log_stt_start_sync(recording_id: int, task_id: str, num_chunks: int, audio_duration: float, file_size: int):
    """Synchronous wrapper for STT start logging."""
    async def _log():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.services.processing_log import ProcessingLogService

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            await ProcessingLogService.log_stt_start(
                session, recording_id, task_id, num_chunks, audio_duration, file_size
            )
    try:
        asyncio.run(_log())
    except Exception as e:
        logger.warning(f"Failed to log STT start: {e}")


def log_stt_complete_sync(recording_id: int, task_id: str, duration_seconds: float,
                          transcript_length: int, word_count: int, audio_duration: float):
    """Synchronous wrapper for STT complete logging."""
    async def _log():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.services.processing_log import ProcessingLogService

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            await ProcessingLogService.log_stt_complete(
                session, recording_id, task_id, duration_seconds,
                transcript_length, word_count, audio_duration
            )
    try:
        asyncio.run(_log())
    except Exception as e:
        logger.warning(f"Failed to log STT complete: {e}")


def log_stt_error_sync(recording_id: int, task_id: str, error_type: str, error_message: str, context: dict | None = None):
    """Synchronous wrapper for STT error logging. Also sets recording status to FAILED."""
    async def _log():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.services.processing_log import ProcessingLogService
        from app.models import Recording, RecordingStatus

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            # Log the error
            await ProcessingLogService.log_stt_error(
                session, recording_id, error_type, error_message, task_id, context
            )
            # Set recording status to FAILED
            result = await session.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = result.scalar_one_or_none()
            if recording:
                recording.status = RecordingStatus.FAILED
                await session.commit()
        await engine.dispose()
    try:
        asyncio.run(_log())
    except Exception as e:
        logger.warning(f"Failed to log STT error: {e}")


def get_redis_client() -> redis.Redis:
    """Get a Redis client for progress updates."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_progress(
    recording_id: int,
    progress: int,
    status: str,
    message: str = "",
    eta_seconds: int | None = None,
) -> None:
    """Publish progress update via Redis Pub/Sub."""
    try:
        r = get_redis_client()
        channel = f"stt:progress:{recording_id}"
        data = {
            "recording_id": recording_id,
            "progress": progress,
            "status": status,
            "message": message,
            "eta_seconds": eta_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.publish(channel, str(data))

        # Also store the last status for SSE reconnection
        r.setex(f"stt:last_status:{recording_id}", 3600, str(data))

    except Exception as e:
        logger.warning(f"Failed to publish progress: {e}")


def get_audio_duration(input_path: str) -> float:
    """
    Get audio duration using ffprobe, with fallback for WebM files without metadata.

    Args:
        input_path: Path to audio file

    Returns:
        Duration in seconds
    """
    # First try ffprobe
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        duration_str = result.stdout.strip()
        if duration_str and duration_str != "N/A":
            try:
                return float(duration_str)
            except ValueError:
                pass

    # Fallback: Use ffmpeg to process file and get actual duration
    logger.info("Duration metadata not available, using ffmpeg to determine duration")
    result = subprocess.run(
        [
            "ffmpeg", "-i", input_path,
            "-f", "null", "-"
        ],
        capture_output=True,
        text=True,
    )

    # Parse duration from ffmpeg stderr (format: time=00:00:20.70)
    # Find all time= matches and use the last one (final duration)
    import re
    time_matches = re.findall(r'time=(\d+):(\d+):(\d+\.?\d*)', result.stderr)
    if time_matches:
        # Use the last match which represents the final duration
        last_match = time_matches[-1]
        hours = int(last_match[0])
        minutes = int(last_match[1])
        seconds = float(last_match[2])
        duration = hours * 3600 + minutes * 60 + seconds
        if duration > 0:
            logger.info(f"Determined duration via ffmpeg: {duration:.1f}s")
            return duration

    # Final fallback: estimate from file size (rough estimate for opus ~32kbps)
    try:
        file_size = os.path.getsize(input_path)
        estimated_duration = file_size / 4000  # ~32kbps = 4000 bytes/sec
        if estimated_duration > 1:
            logger.warning(f"Using estimated duration from file size: {estimated_duration:.1f}s")
            return estimated_duration
    except Exception:
        pass

    raise RuntimeError(f"Could not determine audio duration for {input_path}")


def split_audio_into_chunks(
    input_path: str,
    output_dir: str,
    chunk_minutes: int = 10,
) -> list[str]:
    """
    Split audio file into chunks using ffmpeg.

    Args:
        input_path: Path to input audio file
        output_dir: Directory to save chunks
        chunk_minutes: Duration of each chunk in minutes

    Returns:
        List of chunk file paths
    """
    chunk_seconds = chunk_minutes * 60

    # Get audio duration (handles WebM files without metadata)
    duration = get_audio_duration(input_path)
    num_chunks = int(duration / chunk_seconds) + (1 if duration % chunk_seconds > 0 else 0)

    logger.info(f"Splitting {duration:.1f}s audio into {num_chunks} chunks")

    chunk_paths = []
    for i in range(num_chunks):
        start_time = i * chunk_seconds
        output_path = os.path.join(output_dir, f"chunk_{i:04d}.wav")

        # Use ffmpeg to extract chunk (convert to WAV for Whisper)
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ss", str(start_time),
            "-t", str(chunk_seconds),
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ffmpeg failed for chunk {i}: {result.stderr}")
            raise RuntimeError(f"Failed to split chunk {i}")

        chunk_paths.append(output_path)

    return chunk_paths


@shared_task(
    bind=True,
    name="workers.tasks.stt.process_audio_chunk",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_audio_chunk(
    self,
    chunk_path: str,
    chunk_index: int,
    recording_id: int,
    language: str = "ko",
) -> dict[str, Any]:
    """
    Process a single audio chunk.

    Args:
        chunk_path: Path to the audio chunk
        chunk_index: Index of this chunk
        recording_id: ID of the parent recording
        language: Language code for transcription

    Returns:
        Dict with transcription result
    """
    from app.services.stt import transcribe_audio

    logger.info(f"Processing chunk {chunk_index} for recording {recording_id} (task: {self.request.id})")

    try:
        # Transcribe the chunk
        result = transcribe_audio(chunk_path, language=language)

        # Adjust segment timestamps for this chunk
        chunk_offset = chunk_index * settings.STT_CHUNK_MINUTES * 60
        for segment in result["segments"]:
            segment["start"] += chunk_offset
            segment["end"] += chunk_offset

        logger.info(
            f"Chunk {chunk_index} complete: {len(result['segments'])} segments"
        )

        return {
            "chunk_index": chunk_index,
            "recording_id": recording_id,
            "segments": result["segments"],
            "text": result["text"],
            "language": result["language"],
            "duration": result["duration"],
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Chunk {chunk_index} processing timed out")
        raise

    except Exception as e:
        logger.error(f"Chunk {chunk_index} failed: {e}")
        raise


@shared_task(
    bind=True,
    name="workers.tasks.stt.combine_chunks",
    acks_late=True,
)
def combine_chunks(
    self,
    chunk_results: list[dict[str, Any]],
    recording_id: int,
) -> dict[str, Any]:
    """
    Combine chunk results into final transcript.

    Args:
        chunk_results: List of chunk transcription results
        recording_id: ID of the recording

    Returns:
        Combined transcription result
    """
    logger.info(f"Combining {len(chunk_results)} chunks for recording {recording_id}")

    # Sort by chunk index
    sorted_results = sorted(chunk_results, key=lambda x: x["chunk_index"])

    # Combine all segments
    all_segments = []
    all_text_parts = []
    total_duration = 0

    for result in sorted_results:
        all_segments.extend(result["segments"])
        all_text_parts.append(result["text"])
        total_duration += result["duration"]

    combined = {
        "recording_id": recording_id,
        "segments": all_segments,
        "text": " ".join(all_text_parts),
        "language": sorted_results[0]["language"] if sorted_results else "ko",
        "duration": total_duration,
        "num_chunks": len(chunk_results),
    }

    publish_progress(
        recording_id=recording_id,
        progress=95,
        status="combining",
        message="Combining transcription results",
    )

    return combined


@shared_task(
    bind=True,
    name="workers.tasks.stt.save_transcript",
    acks_late=True,
)
def save_transcript(
    self,
    combined_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Save the combined transcript to the database.

    Args:
        combined_result: Combined transcription result

    Returns:
        Final result with transcript IDs
    """
    from sqlalchemy import select

    from app.models import Recording, RecordingStatus, Transcript

    recording_id = combined_result["recording_id"]
    logger.info(f"Saving transcript for recording {recording_id}")

    # Run async code in sync context
    async def _save():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Get the recording
            result = await session.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = result.scalar_one_or_none()

            if not recording:
                raise ValueError(f"Recording {recording_id} not found")

            # Create transcript record(s)
            # For now, save as a single transcript with all segments
            transcript = Transcript(
                recording_id=recording_id,
                meeting_id=recording.meeting_id,
                chunk_index=0,
                segments=combined_result["segments"],
            )
            session.add(transcript)

            # Update recording status
            recording.status = RecordingStatus.COMPLETED
            recording.duration_seconds = int(combined_result["duration"])

            await session.commit()
            await session.refresh(transcript)

            return transcript.id

    transcript_id = asyncio.run(_save())

    publish_progress(
        recording_id=recording_id,
        progress=100,
        status="completed",
        message="Transcription complete",
    )

    return {
        "recording_id": recording_id,
        "transcript_id": transcript_id,
        "num_segments": len(combined_result["segments"]),
        "duration": combined_result["duration"],
        "status": "completed",
    }


@shared_task(
    bind=True,
    name="workers.tasks.stt.process_recording",
    max_retries=2,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_recording(
    self,
    recording_id: int,
    language: str = "ko",
) -> dict[str, Any]:
    """
    Process a recording: split into chunks, transcribe in parallel, combine.

    Args:
        recording_id: ID of the recording to process
        language: Language code for transcription

    Returns:
        Final transcription result
    """
    from sqlalchemy import select

    logger.info(f"Starting STT processing for recording {recording_id}")

    # Run async code to get recording info
    async def _get_recording():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from app.models import Recording, RecordingStatus, TaskStatusEnum, TaskTracking

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = result.scalar_one_or_none()

            if not recording:
                raise ValueError(f"Recording {recording_id} not found")

            # Update recording status
            recording.status = RecordingStatus.PROCESSING
            await session.commit()

            # Create or update task tracking
            task = TaskTracking(
                task_id=self.request.id,
                task_type="stt",
                recording_id=recording_id,
                status=TaskStatusEnum.PROCESSING,
                started_at=datetime.now(timezone.utc),
            )
            session.add(task)
            await session.commit()

            return {
                "file_path": recording.file_path,
                "meeting_id": recording.meeting_id,
            }

    try:
        recording_info = asyncio.run(_get_recording())
    except Exception as e:
        logger.error(f"Failed to get recording info: {e}")
        raise

    file_path = recording_info["file_path"]

    if not os.path.exists(file_path):
        logger.error(f"Recording file not found: {file_path}")
        log_stt_error_sync(recording_id, self.request.id, "FileNotFound", f"Recording file not found: {file_path}")
        raise FileNotFoundError(f"Recording file not found: {file_path}")

    publish_progress(
        recording_id=recording_id,
        progress=5,
        status="processing",
        message="Starting audio processing",
    )

    # Create temp directory for chunks
    with tempfile.TemporaryDirectory() as temp_dir:
        # Split audio into chunks
        publish_progress(
            recording_id=recording_id,
            progress=10,
            status="splitting",
            message="Splitting audio into chunks",
        )

        try:
            chunk_paths = split_audio_into_chunks(
                file_path,
                temp_dir,
                chunk_minutes=settings.STT_CHUNK_MINUTES,
            )
        except Exception as e:
            logger.error(f"Failed to split audio: {e}")
            log_stt_error_sync(recording_id, self.request.id, "AudioSplitError", str(e))
            raise

        num_chunks = len(chunk_paths)
        logger.info(f"Split into {num_chunks} chunks")

        # Get audio duration and file size for logging
        try:
            audio_duration = get_audio_duration(file_path)
            file_size = os.path.getsize(file_path)
        except Exception:
            audio_duration = 0.0
            file_size = 0

        # Log STT start
        import time
        stt_start_time = time.time()
        log_stt_start_sync(recording_id, self.request.id, num_chunks, audio_duration, file_size)

        publish_progress(
            recording_id=recording_id,
            progress=15,
            status="transcribing",
            message=f"Transcribing {num_chunks} chunks",
            eta_seconds=num_chunks * 60,  # Rough estimate: 1 min per chunk
        )

        # Process chunks sequentially (within same worker to access temp files)
        # This is simpler and avoids temp file issues with distributed chord
        from app.services.stt import transcribe_audio

        chunk_results = []
        for i, chunk_path in enumerate(chunk_paths):
            logger.info(f"Processing chunk {i+1}/{num_chunks} for recording {recording_id}")

            # Update progress
            progress = 15 + int((i / num_chunks) * 75)
            publish_progress(
                recording_id=recording_id,
                progress=progress,
                status="transcribing",
                message=f"Transcribing chunk {i+1}/{num_chunks}",
            )

            try:
                result = transcribe_audio(chunk_path, language=language)

                # Adjust segment timestamps for this chunk
                chunk_offset = i * settings.STT_CHUNK_MINUTES * 60
                for segment in result["segments"]:
                    segment["start"] += chunk_offset
                    segment["end"] += chunk_offset

                chunk_results.append({
                    "chunk_index": i,
                    "recording_id": recording_id,
                    "segments": result["segments"],
                    "text": result["text"],
                    "language": result["language"],
                    "duration": result["duration"],
                })

                logger.info(f"Chunk {i+1}/{num_chunks} complete: {len(result['segments'])} segments")

            except Exception as e:
                logger.error(f"Chunk {i} failed: {e}")
                log_stt_error_sync(recording_id, self.request.id, "ChunkProcessError", str(e), {"chunk_index": i})
                raise

        # Combine results
        logger.info(f"Combining {len(chunk_results)} chunks for recording {recording_id}")

        sorted_results = sorted(chunk_results, key=lambda x: x["chunk_index"])
        all_segments = []
        all_text_parts = []
        total_duration = 0

        for result in sorted_results:
            all_segments.extend(result["segments"])
            all_text_parts.append(result["text"])
            total_duration += result["duration"]

        combined_result = {
            "recording_id": recording_id,
            "segments": all_segments,
            "text": " ".join(all_text_parts),
            "language": sorted_results[0]["language"] if sorted_results else "ko",
            "duration": total_duration,
            "num_chunks": len(chunk_results),
        }

        publish_progress(
            recording_id=recording_id,
            progress=95,
            status="saving",
            message="Saving transcript",
        )

        # Save to database
        async def _save():
            from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
            from sqlalchemy import select
            from app.models import Recording, RecordingStatus, Transcript

            engine = create_async_engine(settings.ASYNC_DATABASE_URL)
            async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                result = await session.execute(
                    select(Recording).where(Recording.id == recording_id)
                )
                recording = result.scalar_one_or_none()

                if not recording:
                    raise ValueError(f"Recording {recording_id} not found")

                # Create transcript record
                # Use original Whisper segments (LLM refine disabled for timestamp accuracy)
                final_segments = combined_result["segments"]
                logger.info(f"Saving {len(final_segments)} Whisper segments")

                transcript = Transcript(
                    recording_id=recording_id,
                    meeting_id=recording.meeting_id,
                    chunk_index=0,
                    segments=final_segments,
                )
                session.add(transcript)

                # Update recording status
                recording.status = RecordingStatus.COMPLETED
                recording.duration_seconds = int(combined_result["duration"])

                await session.commit()
                await session.refresh(transcript)

                return transcript.id

        transcript_id = asyncio.run(_save())

        # Log STT complete
        stt_duration = time.time() - stt_start_time
        full_text = combined_result.get("text", "")
        log_stt_complete_sync(
            recording_id, self.request.id, stt_duration,
            len(full_text), len(full_text.split()), combined_result["duration"]
        )

        publish_progress(
            recording_id=recording_id,
            progress=100,
            status="completed",
            message="Transcription complete",
        )

        return {
            "recording_id": recording_id,
            "transcript_id": transcript_id,
            "num_segments": len(combined_result["segments"]),
            "duration": combined_result["duration"],
            "status": "completed",
        }


@shared_task(
    bind=True,
    name="workers.tasks.stt.reprocess_recording",
    acks_late=True,
)
def reprocess_recording(
    self,
    recording_id: int,
    language: str = "ko",
) -> dict[str, Any]:
    """
    Reprocess a recording (e.g., if initial transcription was unsatisfactory).

    Deletes existing transcripts and reprocesses.
    """
    from sqlalchemy import delete, select

    async def _cleanup():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from app.models import Recording, RecordingStatus, Transcript

        engine = create_async_engine(settings.ASYNC_DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Delete existing transcripts
            await session.execute(
                delete(Transcript).where(Transcript.recording_id == recording_id)
            )

            # Reset recording status
            result = await session.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = result.scalar_one_or_none()
            if recording:
                recording.status = RecordingStatus.UPLOADED
                recording.retry_count += 1

            await session.commit()

    asyncio.run(_cleanup())

    # Trigger reprocessing
    return process_recording.delay(recording_id, language).id
