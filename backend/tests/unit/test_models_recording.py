"""Tests for Recording related models."""

from app.models.recording import Recording, Transcript


class TestRecording:
    """Tests for the Recording model."""

    def test_recording_has_correct_tablename(self):
        """Recording should have tablename 'recordings'."""
        assert Recording.__tablename__ == "recordings"


class TestTranscript:
    """Tests for the Transcript model."""

    def test_transcript_has_correct_tablename(self):
        """Transcript should have tablename 'transcripts'."""
        assert Transcript.__tablename__ == "transcripts"
