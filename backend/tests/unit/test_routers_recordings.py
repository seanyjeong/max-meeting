"""Unit tests for recordings router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.models import Meeting, Recording
from app.models.enums import MeetingStatus, RecordingStatus
from app.schemas.recording import UploadInitResponse


@pytest.fixture
def mock_meeting():
    """Create a mock meeting."""
    now = datetime.now(timezone.utc)
    meeting = Meeting(
        id=1,
        title="Test Meeting",
        status=MeetingStatus.DRAFT,
    )
    meeting.created_at = now
    meeting.updated_at = now
    return meeting


@pytest.fixture
def mock_recording(mock_meeting):
    """Create a mock recording."""
    now = datetime.now(timezone.utc)
    recording = Recording(
        id=1,
        meeting_id=1,
        file_path="/tmp/max-meeting-test/recordings/1/test.webm",
        original_filename="meeting-recording.webm",
        safe_filename="abc123.webm",
        mime_type="audio/webm",
        format="webm",
        duration_seconds=None,
        file_size_bytes=1024000,
        checksum="sha256hash",
        status=RecordingStatus.UPLOADED,
        error_message=None,
        retry_count=0,
    )
    recording.created_at = now
    recording.updated_at = now
    recording.transcripts = []
    return recording


@pytest.fixture
def mock_upload_init_response():
    """Create a mock upload init response."""
    return UploadInitResponse(
        upload_id="upload-123",
        recording_id=1,
        upload_url="/api/v1/recordings/1/upload/upload-123",
        max_chunk_size=10485760,
    )


class TestRecordingsRouter:
    """Tests for recordings API endpoints."""

    @pytest.mark.asyncio
    async def test_create_recording(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_upload_init_response,
    ):
        """Test creating a recording entry."""
        mock_service = MagicMock()
        mock_service.init_upload = AsyncMock(return_value=mock_upload_init_response)

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.post(
                "/api/v1/meetings/1/recordings",
                headers=auth_headers,
                json={
                    "original_filename": "meeting-recording.webm",
                    "format": "webm",
                    "file_size_bytes": 1024000,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["upload_id"] == "upload-123"
        assert data["recording_id"] == 1

    @pytest.mark.asyncio
    async def test_create_recording_meeting_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test creating a recording for non-existent meeting."""
        mock_service = MagicMock()
        mock_service.init_upload = AsyncMock(side_effect=ValueError("Meeting with id 999 not found"))

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.post(
                "/api/v1/meetings/999/recordings",
                headers=auth_headers,
                json={
                    "original_filename": "meeting-recording.webm",
                    "format": "webm",
                },
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_recording(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_recording,
    ):
        """Test getting a recording with transcripts."""
        mock_service = MagicMock()
        mock_service.get_recording = AsyncMock(return_value=mock_recording)

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.get(
                "/api/v1/recordings/1",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["original_filename"] == "meeting-recording.webm"
        assert data["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_get_recording_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting a non-existent recording."""
        mock_service = MagicMock()
        mock_service.get_recording = AsyncMock(side_effect=ValueError("Recording with id 999 not found"))

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.get(
                "/api/v1/recordings/999",
                headers=auth_headers,
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_recording(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_recording,
    ):
        """Test updating a recording status."""
        updated_recording = mock_recording
        updated_recording.status = RecordingStatus.PROCESSING

        mock_service = MagicMock()
        mock_service.update_recording = AsyncMock(return_value=updated_recording)

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.patch(
                "/api/v1/recordings/1",
                headers=auth_headers,
                json={"status": "processing"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"

    @pytest.mark.asyncio
    async def test_delete_recording(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting a recording."""
        mock_service = MagicMock()
        mock_service.delete_recording = AsyncMock(return_value=True)

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.delete(
                "/api/v1/recordings/1",
                headers=auth_headers,
            )

        assert response.status_code == 204


class TestUploadEndpoints:
    """Tests for upload-related endpoints."""

    @pytest.mark.asyncio
    async def test_upload_chunk(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_recording,
        tmp_path,
    ):
        """Test uploading a chunk of the recording."""
        # Set up temp file path that can be created
        mock_recording.file_path = str(tmp_path / "recordings" / "1" / "test.webm")

        mock_service = MagicMock()
        mock_service.get_recording_or_raise = AsyncMock(return_value=mock_recording)

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.post(
                "/api/v1/recordings/1/upload",
                headers={
                    **auth_headers,
                    "Upload-Offset": "0",
                    "Content-Length": "10240",
                    "Upload-Length": "1024000",
                },
                content=b"x" * 10240,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["bytes_received"] == 10240


class TestSSEProgress:
    """Tests for SSE progress endpoint."""

    @pytest.mark.asyncio
    async def test_stream_stt_progress_recording_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test SSE progress for non-existent recording."""
        mock_service = MagicMock()
        mock_service.get_recording_or_raise = AsyncMock(side_effect=ValueError("Recording with id 999 not found"))

        with patch("app.routers.recordings.RecordingService", return_value=mock_service):
            response = await client.get(
                "/api/v1/recordings/999/progress",
                headers=auth_headers,
            )

        assert response.status_code == 404
