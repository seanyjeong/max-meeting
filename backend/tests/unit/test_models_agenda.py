"""Tests for Agenda related models."""

from app.models.base import Base
from app.models.agenda import Agenda, AgendaQuestion


class TestAgenda:
    """Tests for the Agenda model."""

    def test_agenda_has_correct_tablename(self):
        """Agenda should have tablename 'agendas'."""
        assert Agenda.__tablename__ == "agendas"


class TestAgendaQuestion:
    """Tests for the AgendaQuestion model."""

    def test_agenda_question_has_correct_tablename(self):
        """AgendaQuestion should have tablename 'agenda_questions'."""
        assert AgendaQuestion.__tablename__ == "agenda_questions"
