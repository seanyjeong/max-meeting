"""Recording API endpoints."""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Annotated, AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.enums import RecordingStatus
from app.schemas.recording import (
    RecordingCreate,
    RecordingDetailResponse,
    RecordingResponse,
    RecordingUpdate,
    STTProgressEvent,
    UploadInitResponse,
    UploadProgressResponse,
)
from app.services.recording import RecordingService


router = APIRouter(tags=["recordings"])

# 허용된 MIME 타입
ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "application/octet-stream",
}


# ============================================
# Recording Endpoints
# ============================================


@router.post(
    "/meetings/{meeting_id}/recordings",
    response_model=UploadInitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recording(
    meeting_id: int,
    data: RecordingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a recording entry and initialize upload."""
    service = RecordingService(db)
    try:
        upload_info = await service.init_upload(meeting_id, data)
        return upload_info
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/recordings/{recording_id}", response_model=RecordingDetailResponse)
async def get_recording(
    recording_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a recording with its transcript."""
    service = RecordingService(db)
    try:
        recording = await service.get_recording(recording_id, include_transcripts=True)
        return RecordingDetailResponse.model_validate(recording)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/recordings/{recording_id}", response_model=RecordingResponse)
async def update_recording(
    recording_id: int,
    data: RecordingUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a recording status."""
    service = RecordingService(db)
    try:
        recording = await service.update_recording(recording_id, data)
        return RecordingResponse.model_validate(recording)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/recordings/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording(
    recording_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a recording and its file."""
    service = RecordingService(db)
    try:
        await service.delete_recording(recording_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================
# Upload Endpoints (TUS-like)
# ============================================


@router.post("/recordings/{recording_id}/upload", response_model=UploadProgressResponse)
async def upload_chunk(
    recording_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Upload a chunk of the recording file.

    This implements a simplified tus-like protocol for chunked uploads.
    Headers:
        - Upload-Offset: Current offset in bytes
        - Content-Length: Size of this chunk
        - Upload-Length: Total file size (optional, on first chunk)
    """
    service = RecordingService(db)
    try:
        recording = await service.get_recording_or_raise(recording_id)

        # 보안: MIME 타입 검증
        content_type = request.headers.get("Content-Type", "application/octet-stream")
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type: {content_type}",
            )

        # Get upload headers
        upload_offset = int(request.headers.get("Upload-Offset", 0))
        upload_length = request.headers.get("Upload-Length")

        # Read chunk data
        chunk_data = await request.body()

        # Create file path and parent directories
        file_path = Path(recording.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write chunk to file
        if upload_offset == 0:
            # First chunk - create new file
            with open(file_path, "wb") as f:
                f.write(chunk_data)
        else:
            # Subsequent chunk - append to existing file
            with open(file_path, "r+b") as f:
                f.seek(upload_offset)
                f.write(chunk_data)

        # Calculate bytes received
        bytes_received = upload_offset + len(chunk_data)

        # Update recording file size if this is the first chunk
        if upload_length and recording.file_size_bytes is None:
            recording.file_size_bytes = int(upload_length)

        # Check if upload is complete
        is_complete = False
        if recording.file_size_bytes and bytes_received >= recording.file_size_bytes:
            is_complete = True
            # Calculate and store checksum (스트리밍 방식으로 대용량 파일 처리)
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            file_hash = sha256.hexdigest()
            recording.checksum = file_hash
            recording.status = RecordingStatus.UPLOADED

        await db.commit()

        # Trigger STT processing after upload is complete
        if is_complete:
            from workers.tasks.stt import process_recording
            process_recording.delay(recording_id)
            logger.info(f"STT processing triggered for recording {recording_id}")

        return UploadProgressResponse(
            upload_id=recording.safe_filename,
            bytes_received=bytes_received,
            total_bytes=recording.file_size_bytes,
            is_complete=is_complete,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.head("/recordings/{recording_id}/upload")
async def get_upload_status(
    recording_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Get current upload status (HEAD request).

    Returns headers with upload progress info for resume support.
    """
    from fastapi.responses import Response

    service = RecordingService(db)
    try:
        progress = await service.get_upload_progress(recording_id, "")

        return Response(
            headers={
                "Upload-Offset": str(progress.bytes_received),
                "Upload-Length": str(progress.total_bytes or 0),
                "Tus-Resumable": "1.0.0",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================
# SSE Progress Endpoint
# ============================================


async def progress_event_generator(
    recording_id: int,
    redis_client,
    service: RecordingService,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for STT progress."""
    channel = f"stt_progress:{recording_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        # Send initial event
        yield f"event: connected\ndata: {json.dumps({'recording_id': recording_id})}\n\n"

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                event = STTProgressEvent(**data)
                yield f"event: progress\ndata: {event.model_dump_json()}\n\n"

                # Stop if task is complete or failed
                if event.status in ("completed", "failed"):
                    break

            # Heartbeat to keep connection alive
            await asyncio.sleep(0)

    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.get("/recordings/{recording_id}/progress")
async def stream_stt_progress(
    recording_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    SSE endpoint for STT progress.

    This streams real-time progress updates for speech-to-text processing.
    The client should reconnect if the connection is lost.
    """
    service = RecordingService(db)

    try:
        # Verify recording exists
        await service.get_recording_or_raise(recording_id)

        # Get Redis client from app state
        redis_client = request.app.state.redis

        return StreamingResponse(
            progress_event_generator(recording_id, redis_client, service),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
