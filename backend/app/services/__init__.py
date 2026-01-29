"""Services module for MAX Meeting."""

from app.services.encryption import EncryptionService, encrypt_pii, decrypt_pii
from app.services.contact import ContactService, contact_to_response_dict
from app.services.meeting import MeetingService
from app.services.stt import STTService, get_stt_service, transcribe_audio
from app.services.llm import (
    LLMProvider,
    LLMService,
    get_llm_service,
    generate_meeting_summary,
    generate_questions,
)
from app.services.gemini import GeminiProvider
from app.services.speaker_analytics import (
    SpeakerAnalyticsService,
    SpeakerStats,
    get_speaker_analytics_service,
)

__all__ = [
    # Encryption
    "EncryptionService",
    "encrypt_pii",
    "decrypt_pii",
    # Contact
    "ContactService",
    "contact_to_response_dict",
    # Meeting
    "MeetingService",
    # STT
    "STTService",
    "get_stt_service",
    "transcribe_audio",
    # LLM
    "LLMProvider",
    "LLMService",
    "get_llm_service",
    "generate_meeting_summary",
    "generate_questions",
    # Providers
    "GeminiProvider",
    # Speaker Analytics
    "SpeakerAnalyticsService",
    "SpeakerStats",
    "get_speaker_analytics_service",
]
