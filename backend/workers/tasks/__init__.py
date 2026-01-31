"""Celery tasks for MAX Meeting."""

from workers.tasks.stt import process_recording, process_audio_chunk
from workers.tasks.llm import generate_meeting_result, generate_questions
from workers.tasks.upload import finalize_upload
from workers.tasks.cleanup import cleanup_old_recordings

__all__ = [
    # STT tasks
    "process_recording",
    "process_audio_chunk",
    # LLM tasks
    "generate_meeting_result",
    "generate_questions",
    # Upload tasks
    "finalize_upload",
    # Cleanup tasks
    "cleanup_old_recordings",
]
