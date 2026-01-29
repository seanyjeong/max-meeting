"""Tests for Note related models."""

from app.models.note import ManualNote, Sketch


class TestManualNote:
    """Tests for the ManualNote model."""

    def test_manual_note_has_correct_tablename(self):
        """ManualNote should have tablename 'manual_notes'."""
        assert ManualNote.__tablename__ == "manual_notes"


class TestSketch:
    """Tests for the Sketch model."""

    def test_sketch_has_correct_tablename(self):
        """Sketch should have tablename 'sketches'."""
        assert Sketch.__tablename__ == "sketches"
