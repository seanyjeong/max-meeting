"""
Speech-to-Text service using faster-whisper with pyannote speaker diarization.

Provides transcription functionality for audio files with speaker identification.
Based on spec Section 4 (Phase 4: STT + upload).
"""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """A segment of transcribed audio."""

    start: float
    end: float
    text: str
    confidence: float
    speaker: str | None = None


@dataclass
class TranscriptResult:
    """Result of audio transcription."""

    text: str
    segments: list[TranscriptSegment]
    language: str
    duration: float
    speakers: list[str] | None = None


class STTService:
    """Speech-to-text service using faster-whisper with pyannote diarization."""

    _model = None  # Class-level Whisper model caching
    _diarization_pipeline = None  # Class-level diarization pipeline caching
    _model_lock = threading.Lock()
    _diarization_lock = threading.Lock()

    def __init__(self):
        self.settings = get_settings()
        self._ensure_model_loaded()

    def _ensure_model_loaded(self) -> None:
        """Ensure Whisper model is loaded (thread-safe)."""
        if STTService._model is None:
            with STTService._model_lock:
                if STTService._model is None:  # Double-check pattern
                    try:
                        from faster_whisper import WhisperModel

                        logger.info(
                            f"Loading Whisper model: {self.settings.WHISPER_MODEL} "
                            f"on {self.settings.WHISPER_DEVICE}"
                        )

                        # Use int8 quantization for CPU, float16 for CUDA
                        compute_type = "int8" if self.settings.WHISPER_DEVICE == "cpu" else "float16"

                        STTService._model = WhisperModel(
                            self.settings.WHISPER_MODEL,
                            device=self.settings.WHISPER_DEVICE,
                            compute_type=compute_type,
                        )

                        logger.info("Whisper model loaded successfully")

                    except ImportError:
                        logger.error("faster-whisper not installed")
                        raise RuntimeError("faster-whisper is not installed")
                    except Exception as e:
                        logger.error(f"Failed to load Whisper model: {e}")
                        raise

    def _ensure_diarization_loaded(self) -> bool:
        """Ensure diarization pipeline is loaded (thread-safe)."""
        if STTService._diarization_pipeline is None:
            with STTService._diarization_lock:
                if STTService._diarization_pipeline is None:  # Double-check pattern
                    try:
                        from pyannote.audio import Pipeline

                        hf_token = self.settings.HUGGINGFACE_TOKEN
                        if not hf_token:
                            logger.warning(
                                "HUGGINGFACE_TOKEN not set - speaker diarization disabled"
                            )
                            return False

                        logger.info("Loading pyannote speaker diarization pipeline...")

                        STTService._diarization_pipeline = Pipeline.from_pretrained(
                            "pyannote/speaker-diarization-3.1",
                            use_auth_token=hf_token,
                        )

                        # Move to appropriate device
                        if self.settings.WHISPER_DEVICE == "cuda":
                            import torch
                            STTService._diarization_pipeline.to(torch.device("cuda"))

                        logger.info("Pyannote diarization pipeline loaded successfully")
                        return True

                    except ImportError:
                        logger.warning("pyannote.audio not installed - speaker diarization disabled")
                        return False
                    except Exception as e:
                        logger.warning(f"Failed to load pyannote pipeline: {e}")
                        return False
        return True

    def diarize_audio(self, file_path: str) -> dict[str, list[tuple[float, float]]]:
        """
        Run speaker diarization on an audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            dict with speaker labels as keys and list of (start, end) tuples as values
        """
        if not self._ensure_diarization_loaded():
            return {}

        try:
            logger.info(f"Running speaker diarization on {file_path}")
            diarization = STTService._diarization_pipeline(file_path)

            # Convert diarization to dict format
            speaker_segments: dict[str, list[tuple[float, float]]] = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if speaker not in speaker_segments:
                    speaker_segments[speaker] = []
                speaker_segments[speaker].append((turn.start, turn.end))

            logger.info(f"Diarization complete: {len(speaker_segments)} speakers detected")
            return speaker_segments

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return {}

    def _find_speaker_for_segment(
        self,
        start: float,
        end: float,
        diarization: dict[str, list[tuple[float, float]]],
    ) -> str | None:
        """
        Find the speaker for a given time range based on diarization results.

        Uses overlap calculation to find the speaker with the most overlap.
        """
        if not diarization:
            return None

        best_speaker = None
        best_overlap = 0.0

        for speaker, segments in diarization.items():
            total_overlap = 0.0
            for seg_start, seg_end in segments:
                # Calculate overlap
                overlap_start = max(start, seg_start)
                overlap_end = min(end, seg_end)
                if overlap_end > overlap_start:
                    total_overlap += overlap_end - overlap_start

            if total_overlap > best_overlap:
                best_overlap = total_overlap
                best_speaker = speaker

        return best_speaker

    def transcribe_audio(
        self,
        file_path: str,
        language: str = "ko",
        enable_diarization: bool = True,
    ) -> dict[str, Any]:
        """
        Transcribe an audio file to text with optional speaker diarization.

        Args:
            file_path: Path to the audio file
            language: Language code (default: "ko" for Korean)
            enable_diarization: Whether to run speaker diarization (default: True)

        Returns:
            dict with keys:
                - text: Full transcription text
                - segments: List of segment dicts with start, end, text, confidence, speaker
                - language: Detected/used language
                - duration: Total audio duration in seconds
                - speakers: List of unique speaker labels (if diarization enabled)
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        logger.info(f"Starting transcription of {file_path}")

        # Run diarization in parallel with transcription if enabled
        diarization = {}
        if enable_diarization:
            diarization = self.diarize_audio(file_path)

        try:
            segments_iter, info = STTService._model.transcribe(
                file_path,
                language=language,
                beam_size=5,
                best_of=5,
                patience=1.0,
                length_penalty=1.0,
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6,
                condition_on_previous_text=True,
                initial_prompt=None,
                word_timestamps=False,
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": 500,
                    "speech_pad_ms": 200,
                },
            )

            # Convert segments to list
            segments = []
            full_text_parts = []
            speakers_found = set()

            for segment in segments_iter:
                # Find speaker for this segment
                speaker = self._find_speaker_for_segment(
                    segment.start, segment.end, diarization
                )
                if speaker:
                    speakers_found.add(speaker)

                segment_dict = {
                    "start": round(segment.start, 3),
                    "end": round(segment.end, 3),
                    "text": segment.text.strip(),
                    "confidence": round(
                        segment.avg_logprob if hasattr(segment, "avg_logprob") else 0.0,
                        4
                    ),
                    "speaker": speaker,
                }
                segments.append(segment_dict)
                full_text_parts.append(segment.text.strip())

            full_text = " ".join(full_text_parts)

            result = {
                "text": full_text,
                "segments": segments,
                "language": info.language,
                "duration": round(info.duration, 3),
                "speakers": sorted(list(speakers_found)) if speakers_found else None,
            }

            logger.info(
                f"Transcription complete: {len(segments)} segments, "
                f"{info.duration:.1f}s duration, {len(speakers_found)} speakers"
            )

            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise


def transcribe_audio(
    file_path: str,
    language: str = "ko",
    enable_diarization: bool = True,
) -> dict[str, Any]:
    """
    Convenience function to transcribe audio with speaker diarization.

    Args:
        file_path: Path to the audio file
        language: Language code (default: "ko" for Korean)
        enable_diarization: Whether to run speaker diarization (default: True)

    Returns:
        dict with text, segments (with speaker labels), language, duration, and speakers
    """
    service = STTService()
    return service.transcribe_audio(file_path, language, enable_diarization)


def get_stt_service() -> STTService:
    """Get an STT service instance."""
    return STTService()
