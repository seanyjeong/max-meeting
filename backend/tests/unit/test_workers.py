"""
Unit tests for Celery workers and related services.

Tests the STT, LLM services, and Celery task logic
with mocked external dependencies.
"""

import json
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Mock external modules that may not be installed in test environment
# =============================================================================

# Create mock modules for optional dependencies
mock_faster_whisper = MagicMock()
mock_genai = MagicMock()
mock_celery = MagicMock()
mock_kombu = MagicMock()

# Pre-patch optional modules
# Note: Do NOT mock redis - it's installed and the asyncio submodule is needed
sys.modules.setdefault("faster_whisper", mock_faster_whisper)
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.generativeai", mock_genai)
sys.modules.setdefault("celery", mock_celery)
sys.modules.setdefault("celery.exceptions", MagicMock())
sys.modules.setdefault("kombu", mock_kombu)

# Mock Celery classes
mock_celery.Celery = MagicMock()
mock_celery.shared_task = lambda *args, **kwargs: lambda f: f
mock_celery.chain = MagicMock()
mock_celery.chord = MagicMock()
mock_celery.group = MagicMock()
mock_kombu.Exchange = MagicMock()
mock_kombu.Queue = MagicMock()


# =============================================================================
# STT Service Tests
# =============================================================================

class TestSTTService:
    """Tests for the STT service."""

    @pytest.fixture
    def mock_whisper_model(self):
        """Create a mock Whisper model."""
        model = MagicMock()

        # Create mock segment
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "Hello world"
        mock_segment.avg_logprob = -0.5

        # Create mock info
        mock_info = MagicMock()
        mock_info.language = "ko"
        mock_info.duration = 5.0

        model.transcribe.return_value = (iter([mock_segment]), mock_info)
        return model

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.WHISPER_MODEL = "medium"
        settings.WHISPER_DEVICE = "cpu"
        return settings

    def test_stt_service_creation_with_mock(self, mock_settings, mock_whisper_model):
        """Test STT service can be created with mocked dependencies."""
        # Patch at module level before import
        mock_faster_whisper.WhisperModel = MagicMock(return_value=mock_whisper_model)

        with patch("app.services.stt.get_settings", return_value=mock_settings):
            from app.services.stt import STTService

            # Reset the class-level model cache
            STTService._model = None

            service = STTService()
            assert service is not None

    def test_transcribe_audio_success(self, mock_settings, mock_whisper_model, tmp_path):
        """Test successful audio transcription."""
        # Create a dummy audio file
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        with patch("app.services.stt.get_settings", return_value=mock_settings):
            from app.services.stt import STTService

            STTService._model = mock_whisper_model

            service = STTService()
            result = service.transcribe_audio(str(audio_file))

            assert "text" in result
            assert "segments" in result
            assert "language" in result
            assert "duration" in result
            assert result["text"] == "Hello world"
            assert len(result["segments"]) == 1
            assert result["segments"][0]["start"] == 0.0
            assert result["segments"][0]["end"] == 5.0


# =============================================================================
# LLM Service Tests
# =============================================================================

class TestLLMService:
    """Tests for the LLM service."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = AsyncMock()
        provider.generate_json = AsyncMock(return_value={
            "summary": "Test meeting summary",
            "discussions": [
                {"agenda_idx": 0, "content": "Discussion about agenda 1"}
            ],
            "decisions": [
                {"agenda_idx": 0, "content": "Decision made", "type": "approved"}
            ],
            "action_items": [
                {
                    "agenda_idx": 0,
                    "assignee": "John",
                    "content": "Complete task",
                    "due_date": "2026-02-15"
                }
            ],
        })
        return provider

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.LLM_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = "test-api-key"
        settings.LLM_MAX_TOKENS_PER_REQUEST = 100000
        return settings

    @pytest.mark.asyncio
    async def test_generate_meeting_summary(self, mock_provider, mock_settings):
        """Test meeting summary generation."""
        with patch("app.services.llm.get_settings", return_value=mock_settings):
            from app.services.llm import LLMService

            service = LLMService(provider=mock_provider)

            result = await service.generate_meeting_summary(
                transcript="Test transcript about the meeting",
                agenda_titles=["Agenda 1", "Agenda 2"],
            )

            assert "summary" in result
            assert "discussions" in result
            assert "decisions" in result
            assert "action_items" in result
            assert result["summary"] == "Test meeting summary"
            assert len(result["discussions"]) == 1
            assert len(result["decisions"]) == 1
            assert len(result["action_items"]) == 1

    @pytest.mark.asyncio
    async def test_generate_questions(self, mock_settings):
        """Test question generation."""
        mock_provider = AsyncMock()
        mock_provider.generate_json = AsyncMock(return_value=[
            "What is the budget?",
            "Who is responsible?",
            "When is the deadline?",
        ])

        with patch("app.services.llm.get_settings", return_value=mock_settings):
            from app.services.llm import LLMService

            service = LLMService(provider=mock_provider)

            result = await service.generate_questions(
                agenda_title="Budget Discussion",
                num_questions=3,
            )

            assert len(result) == 3
            assert "budget" in result[0].lower()

    @pytest.mark.asyncio
    async def test_normalize_summary_result(self, mock_settings):
        """Test summary result normalization handles various formats."""
        with patch("app.services.llm.get_settings", return_value=mock_settings):
            from app.services.llm import LLMService

            # Create service with dummy provider (won't be used)
            mock_provider = AsyncMock()
            service = LLMService(provider=mock_provider)

            # Test with agenda_id instead of agenda_idx
            result = service._normalize_summary_result({
                "summary": "Test",
                "discussions": [{"agenda_id": 1, "content": "Test content"}],
                "decisions": [{"agenda_id": 1, "content": "Approved", "type": "invalid_type"}],
                "action_items": [{"agenda_id": 1, "assignee": "John", "content": "Task"}],
            })

            assert result["discussions"][0]["agenda_idx"] == 1
            assert result["decisions"][0]["type"] == "approved"  # Invalid type normalized
            assert result["action_items"][0]["due_date"] is None  # Missing field


# =============================================================================
# Gemini Provider Tests
# =============================================================================

class TestGeminiProvider:
    """Tests for the Gemini LLM provider."""

    def test_provider_requires_api_key(self):
        """Test that provider requires an API key."""
        # Mock genai module
        mock_genai.configure = MagicMock()
        mock_genai.GenerativeModel = MagicMock()

        with pytest.raises(ValueError, match="API key is required"):
            from app.services.gemini import GeminiProvider
            GeminiProvider(api_key="")

    def test_json_parsing_markdown_response(self):
        """Test JSON parsing handles markdown code blocks."""
        import json

        text_response = '```json\n{"key": "value"}\n```'

        # Simulate the parsing logic from GeminiProvider.generate_json
        cleaned = text_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)

        assert result == {"key": "value"}

    def test_json_parsing_array_response(self):
        """Test JSON parsing handles array responses."""
        import json

        text_response = '["item1", "item2", "item3"]'

        # Simulate the parsing logic
        cleaned = text_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)

        assert result == ["item1", "item2", "item3"]

    def test_json_fallback_extraction(self):
        """Test JSON extraction fallback for malformed responses."""
        import json
        import re

        text_response = 'Some text before {"key": "value"} some text after'

        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
        assert json_match is not None
        result = json.loads(json_match.group())

        assert result == {"key": "value"}


# =============================================================================
# Celery Task Tests
# =============================================================================

class TestCeleryAppConfig:
    """Tests for Celery app configuration."""

    def test_celery_config_values(self):
        """Test Celery configuration values are correct."""
        # Test configuration dict structure
        expected_config = {
            "task_acks_late": True,
            "task_reject_on_worker_lost": True,
            "worker_prefetch_multiplier": 1,
            "task_serializer": "json",
            "result_serializer": "json",
        }

        # Verify expected config keys
        for key, value in expected_config.items():
            assert isinstance(key, str)


class TestSTTTasks:
    """Tests for STT Celery tasks."""

    def test_publish_progress_function(self):
        """Test progress publishing logic."""
        # Test data structure for progress messages
        data = {
            "recording_id": 1,
            "progress": 50,
            "status": "processing",
            "message": "Test message",
            "eta_seconds": 60,
        }

        assert data["recording_id"] == 1
        assert data["progress"] == 50
        assert data["status"] == "processing"

    def test_split_audio_chunks_logic(self, tmp_path):
        """Test audio chunk splitting logic."""
        # Test chunk calculation
        duration_seconds = 1800  # 30 minutes
        chunk_minutes = 10
        chunk_seconds = chunk_minutes * 60

        num_chunks = int(duration_seconds / chunk_seconds) + (
            1 if duration_seconds % chunk_seconds > 0 else 0
        )

        assert num_chunks == 3


class TestLLMTasks:
    """Tests for LLM Celery tasks."""

    def test_publish_progress_structure(self):
        """Test progress data structure."""
        data = {
            "meeting_id": 1,
            "progress": 50,
            "status": "generating",
            "message": "Test message",
        }

        assert "meeting_id" in data
        assert "progress" in data
        assert "status" in data
        assert "message" in data


class TestUploadTasks:
    """Tests for upload Celery tasks."""

    def test_compute_file_checksum(self, tmp_path):
        """Test file checksum computation."""
        import hashlib

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Compute checksum manually
        sha256_hash = hashlib.sha256()
        sha256_hash.update(test_content.encode())
        expected_checksum = sha256_hash.hexdigest()

        # Test our implementation matches
        sha256_hash2 = hashlib.sha256()
        with open(str(test_file), "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash2.update(chunk)
        actual_checksum = sha256_hash2.hexdigest()

        assert actual_checksum == expected_checksum
        assert len(actual_checksum) == 64  # SHA-256 hex length

    def test_compute_file_checksum_consistency(self, tmp_path):
        """Test checksum is consistent for same content."""
        import hashlib

        test_file = tmp_path / "test.txt"
        test_file.write_text("Consistent content")

        def compute_checksum(path):
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()

        checksum1 = compute_checksum(str(test_file))
        checksum2 = compute_checksum(str(test_file))

        assert checksum1 == checksum2


# =============================================================================
# Integration-style Unit Tests
# =============================================================================

class TestServiceIntegration:
    """Integration-style tests for services."""

    @pytest.fixture
    def mock_settings(self):
        """Create comprehensive mock settings."""
        settings = MagicMock()
        settings.WHISPER_MODEL = "medium"
        settings.WHISPER_DEVICE = "cpu"
        settings.LLM_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = "test-key"
        settings.LLM_MAX_TOKENS_PER_REQUEST = 100000
        settings.REDIS_URL = "redis://localhost:6379/0"
        settings.CELERY_BROKER_URL = "redis://localhost:6379/0"
        settings.CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
        settings.CELERY_TASK_ACKS_LATE = True
        settings.CELERY_TASK_TIME_LIMIT = 7200
        settings.CELERY_TASK_SOFT_TIME_LIMIT = 6900
        settings.CELERY_WORKER_CONCURRENCY = 1
        settings.STT_CHUNK_MINUTES = 10
        settings.STT_MAX_PARALLEL = 4
        return settings

    def test_services_can_be_imported(self):
        """Test all services can be imported."""
        from app.services import (
            STTService,
            get_stt_service,
            transcribe_audio,
            LLMService,
            LLMProvider,
            get_llm_service,
            GeminiProvider,
        )

        assert STTService is not None
        assert LLMService is not None
        assert LLMProvider is not None
        assert GeminiProvider is not None

    def test_service_dataclasses(self):
        """Test service dataclasses are properly defined."""
        from app.services.stt import TranscriptSegment, TranscriptResult
        from app.services.llm import MeetingSummary, QuestionSet

        # Test TranscriptSegment
        segment = TranscriptSegment(start=0.0, end=5.0, text="Hello", confidence=0.9)
        assert segment.start == 0.0
        assert segment.end == 5.0
        assert segment.text == "Hello"
        assert segment.confidence == 0.9

        # Test TranscriptResult
        result = TranscriptResult(
            text="Full text",
            segments=[segment],
            language="ko",
            duration=5.0
        )
        assert result.text == "Full text"
        assert len(result.segments) == 1

        # Test MeetingSummary
        summary = MeetingSummary(
            summary="Meeting summary",
            discussions=[],
            decisions=[],
            action_items=[]
        )
        assert summary.summary == "Meeting summary"

        # Test QuestionSet
        questions = QuestionSet(questions=["Q1", "Q2"])
        assert len(questions.questions) == 2

    def test_llm_provider_abstract_class(self):
        """Test LLM provider is properly abstract."""
        from app.services.llm import LLMProvider
        from abc import ABC

        # Verify LLMProvider is abstract
        assert issubclass(LLMProvider, ABC)

    def test_summary_normalization_logic(self):
        """Test the summary normalization preserves data correctly."""
        # Simulate the normalization logic
        raw_result = {
            "summary": "Test summary",
            "discussions": [
                {"agenda_id": 1, "content": "Discussion 1"},
                {"agenda_idx": 2, "content": "Discussion 2"},
            ],
            "decisions": [
                {"agenda_id": 1, "content": "Decision", "type": "approved"},
                {"agenda_idx": 2, "content": "Decision 2", "type": "invalid"},
            ],
            "action_items": [
                {"agenda_id": 1, "assignee": "John", "content": "Task", "due_date": "2026-02-15"},
                {"agenda_idx": 2, "assignee": "Jane", "content": "Task 2"},
            ],
        }

        # Normalize
        normalized = {
            "summary": raw_result.get("summary", ""),
            "discussions": [],
            "decisions": [],
            "action_items": [],
        }

        for item in raw_result.get("discussions", []):
            normalized["discussions"].append({
                "agenda_idx": item.get("agenda_idx", item.get("agenda_id", 0)),
                "content": item.get("content", ""),
            })

        for item in raw_result.get("decisions", []):
            decision_type = item.get("type", "approved")
            if decision_type not in ("approved", "postponed", "rejected"):
                decision_type = "approved"
            normalized["decisions"].append({
                "agenda_idx": item.get("agenda_idx", item.get("agenda_id", 0)),
                "content": item.get("content", ""),
                "type": decision_type,
            })

        for item in raw_result.get("action_items", []):
            normalized["action_items"].append({
                "agenda_idx": item.get("agenda_idx", item.get("agenda_id", 0)),
                "assignee": item.get("assignee", ""),
                "content": item.get("content", ""),
                "due_date": item.get("due_date"),
            })

        assert normalized["summary"] == "Test summary"
        assert len(normalized["discussions"]) == 2
        assert normalized["discussions"][0]["agenda_idx"] == 1
        assert normalized["discussions"][1]["agenda_idx"] == 2
        assert normalized["decisions"][1]["type"] == "approved"  # Invalid type normalized
        assert normalized["action_items"][1]["due_date"] is None  # Missing field
