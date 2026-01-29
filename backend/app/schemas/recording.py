"""Recording-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RecordingStatus


# ============================================
# Transcript Schemas
# ============================================


class TranscriptSegment(BaseModel):
    """Schema for a single transcript segment."""

    start: float
    end: float
    text: str
    speaker: str | None = None
    confidence: float | None = None


class TranscriptResponse(BaseModel):
    """Schema for transcript response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    recording_id: int
    meeting_id: int
    chunk_index: int
    segments: list[TranscriptSegment]
    created_at: datetime


# ============================================
# Recording Schemas
# ============================================


class RecordingBase(BaseModel):
    """Base schema for recordings."""

    original_filename: str | None = None
    format: str = Field(default="webm")
    duration_seconds: int | None = None


class RecordingCreate(BaseModel):
    """Schema for creating a recording entry."""

    original_filename: str | None = Field(default=None, max_length=200)
    format: str = Field(default="webm", max_length=20)
    file_size_bytes: int | None = Field(default=None, ge=0)


class RecordingUpdate(BaseModel):
    """Schema for updating a recording."""

    status: RecordingStatus | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    error_message: str | None = None


class RecordingResponse(BaseModel):
    """Schema for recording response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    original_filename: str | None
    safe_filename: str
    mime_type: str
    format: str
    duration_seconds: int | None
    file_size_bytes: int | None
    status: RecordingStatus
    error_message: str | None
    retry_count: int
    created_at: datetime


class RecordingDetailResponse(RecordingResponse):
    """Schema for recording with transcripts."""

    transcripts: list[TranscriptResponse] = []


# ============================================
# Upload Schemas
# ============================================


class UploadInitResponse(BaseModel):
    """Response when initializing an upload."""

    upload_id: str
    recording_id: int
    upload_url: str
    max_chunk_size: int


class UploadProgressResponse(BaseModel):
    """Response for upload progress."""

    upload_id: str
    bytes_received: int
    total_bytes: int | None
    is_complete: bool


class ChunkUploadRequest(BaseModel):
    """Request for uploading a chunk."""

    chunk_index: int = Field(..., ge=0)
    is_final: bool = Field(default=False)


# ============================================
# STT Progress Schemas
# ============================================


class STTProgressEvent(BaseModel):
    """SSE event for STT progress."""

    task_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)
    eta_seconds: int | None = None
    current_chunk: int | None = None
    total_chunks: int | None = None
    error_message: str | None = None
