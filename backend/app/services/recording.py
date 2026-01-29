"""Recording service for business logic."""

import hashlib
import uuid
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Meeting, Recording
from app.models.enums import RecordingStatus
from app.schemas.recording import (
    RecordingCreate,
    RecordingUpdate,
    UploadInitResponse,
    UploadProgressResponse,
)


class RecordingService:
    """Service for recording-related operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_meeting_or_raise(self, meeting_id: int) -> Meeting:
        """Get meeting by ID or raise exception."""
        result = await self.db.execute(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.deleted_at.is_(None),
            )
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            raise ValueError(f"Meeting with id {meeting_id} not found")
        return meeting

    async def get_recording_or_raise(
        self,
        recording_id: int,
        include_transcripts: bool = False,
    ) -> Recording:
        """Get recording by ID or raise exception."""
        query = select(Recording).where(Recording.id == recording_id)

        if include_transcripts:
            query = query.options(selectinload(Recording.transcripts))

        result = await self.db.execute(query)
        recording = result.scalar_one_or_none()
        if not recording:
            raise ValueError(f"Recording with id {recording_id} not found")
        return recording

    async def create_recording(
        self,
        meeting_id: int,
        data: RecordingCreate,
    ) -> Recording:
        """Create a new recording entry."""
        await self.get_meeting_or_raise(meeting_id)

        # Generate safe filename
        safe_filename = f"{uuid.uuid4()}.{data.format}"

        # Build file path
        from app.config import get_settings
        settings = get_settings()
        file_path = str(
            Path(settings.RECORDINGS_PATH) / str(meeting_id) / safe_filename
        )

        # Placeholder checksum (will be updated after upload)
        checksum = hashlib.sha256(safe_filename.encode()).hexdigest()

        # Determine MIME type
        mime_types = {
            "webm": "audio/webm",
            "mp4": "audio/mp4",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg",
            "wav": "audio/wav",
        }
        mime_type = mime_types.get(data.format, "audio/webm")

        recording = Recording(
            meeting_id=meeting_id,
            file_path=file_path,
            original_filename=data.original_filename,
            safe_filename=safe_filename,
            mime_type=mime_type,
            format=data.format,
            file_size_bytes=data.file_size_bytes,
            checksum=checksum,
            status=RecordingStatus.UPLOADED,
        )

        self.db.add(recording)
        await self.db.flush()
        await self.db.refresh(recording)

        return recording

    async def get_recording(
        self,
        recording_id: int,
        include_transcripts: bool = True,
    ) -> Recording:
        """Get a recording by ID."""
        return await self.get_recording_or_raise(
            recording_id,
            include_transcripts=include_transcripts,
        )

    async def update_recording(
        self,
        recording_id: int,
        data: RecordingUpdate,
    ) -> Recording:
        """Update a recording."""
        recording = await self.get_recording_or_raise(recording_id)

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(recording, key, value)

        await self.db.flush()
        await self.db.refresh(recording)

        return recording

    async def delete_recording(self, recording_id: int) -> bool:
        """Delete a recording and its file."""
        recording = await self.get_recording_or_raise(recording_id)

        # Delete file from storage
        file_path = Path(recording.file_path)
        if file_path.exists():
            file_path.unlink()

        await self.db.delete(recording)
        await self.db.flush()

        return True

    # ============================================
    # Upload Operations (TUS-like)
    # ============================================

    async def init_upload(
        self,
        meeting_id: int,
        data: RecordingCreate,
    ) -> UploadInitResponse:
        """Initialize a chunked upload."""
        recording = await self.create_recording(meeting_id, data)

        upload_id = str(uuid.uuid4())

        return UploadInitResponse(
            upload_id=upload_id,
            recording_id=recording.id,
            upload_url=f"/api/v1/recordings/{recording.id}/upload/{upload_id}",
            max_chunk_size=10 * 1024 * 1024,  # 10MB chunks
        )

    async def get_upload_progress(
        self,
        recording_id: int,
        upload_id: str,
    ) -> UploadProgressResponse:
        """Get upload progress for a recording."""
        recording = await self.get_recording_or_raise(recording_id)

        # Check how much has been uploaded
        file_path = Path(recording.file_path)
        bytes_received = file_path.stat().st_size if file_path.exists() else 0

        return UploadProgressResponse(
            upload_id=upload_id,
            bytes_received=bytes_received,
            total_bytes=recording.file_size_bytes,
            is_complete=recording.status != RecordingStatus.UPLOADED,
        )

    async def finalize_upload(
        self,
        recording_id: int,
        checksum: str,
    ) -> Recording:
        """Finalize upload and update checksum."""
        recording = await self.get_recording_or_raise(recording_id)

        # Verify checksum
        file_path = Path(recording.file_path)
        if file_path.exists():
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            if file_hash != checksum:
                raise ValueError("Checksum mismatch")

        recording.checksum = checksum
        recording.status = RecordingStatus.UPLOADED

        await self.db.flush()
        await self.db.refresh(recording)

        return recording

    # ============================================
    # SSE Progress
    # ============================================

    async def stream_stt_progress(
        self,
        recording_id: int,
        redis_client,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream STT progress via SSE.

        This is a generator that yields progress events.
        """
        await self.get_recording_or_raise(recording_id)

        channel = f"stt_progress:{recording_id}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    import json

                    data = json.loads(message["data"])
                    yield data

                    # Stop if task is complete
                    if data.get("status") in ("completed", "failed"):
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
