"""Unit tests for agendas router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.models import Agenda, AgendaQuestion, Meeting
from app.models.enums import AgendaStatus, MeetingStatus


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
def mock_agenda(mock_meeting):
    """Create a mock agenda."""
    now = datetime.now(timezone.utc)
    agenda = Agenda(
        id=1,
        meeting_id=1,
        title="Test Agenda",
        description="Test description",
        order_num=0,
        status=AgendaStatus.PENDING,
    )
    agenda.created_at = now
    agenda.updated_at = now
    agenda.questions = []
    return agenda


@pytest.fixture
def mock_question(mock_agenda):
    """Create a mock question."""
    question = AgendaQuestion(
        id=1,
        agenda_id=1,
        question="What is the budget?",
        order_num=0,
        is_generated=True,
        answered=False,
    )
    return question


class TestAgendasRouter:
    """Tests for agendas API endpoints."""

    @pytest.mark.asyncio
    async def test_list_agendas_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_meeting,
    ):
        """Test listing agendas when none exist."""
        mock_service = MagicMock()
        mock_service.list_agendas = AsyncMock(return_value=[])

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.get(
                "/api/v1/meetings/1/agendas",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_list_agendas_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_meeting,
        mock_agenda,
    ):
        """Test listing agendas with existing data."""
        # Need to set questions attribute for model_validate
        mock_agenda.questions = []

        mock_service = MagicMock()
        mock_service.list_agendas = AsyncMock(return_value=[mock_agenda])

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.get(
                "/api/v1/meetings/1/agendas",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Test Agenda"

    @pytest.mark.asyncio
    async def test_list_agendas_meeting_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test listing agendas for non-existent meeting."""
        mock_service = MagicMock()
        mock_service.list_agendas = AsyncMock(side_effect=ValueError("Meeting with id 999 not found"))

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.get(
                "/api/v1/meetings/999/agendas",
                headers=auth_headers,
            )

        assert response.status_code == 404
        # Error response uses custom format with 'error' key
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data
        if "error" in error_data:
            assert "not found" in error_data["error"]["message"].lower()
        else:
            assert "not found" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_agenda(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_meeting,
        mock_agenda,
    ):
        """Test creating a new agenda."""
        # Need to set questions attribute for model_validate
        mock_agenda.questions = []

        mock_service = MagicMock()
        mock_service.create_agenda = AsyncMock(return_value=mock_agenda)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            with patch("app.routers.agendas.generate_questions", new_callable=AsyncMock, return_value=[]):
                response = await client.post(
                    "/api/v1/meetings/1/agendas",
                    headers=auth_headers,
                    json={
                        "title": "New Agenda",
                        "description": "New description",
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Agenda"

    @pytest.mark.asyncio
    async def test_create_agenda_validation_error(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test creating an agenda with invalid data."""
        response = await client.post(
            "/api/v1/meetings/1/agendas",
            headers=auth_headers,
            json={
                "title": "",  # Empty title should fail validation
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_agenda(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_agenda,
    ):
        """Test getting a specific agenda."""
        mock_agenda.questions = []

        mock_service = MagicMock()
        mock_service.get_agenda_or_raise = AsyncMock(return_value=mock_agenda)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.get(
                "/api/v1/agendas/1",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Test Agenda"

    @pytest.mark.asyncio
    async def test_update_agenda(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_agenda,
    ):
        """Test updating an agenda."""
        mock_agenda.questions = []
        updated_agenda = mock_agenda
        updated_agenda.title = "Updated Title"

        mock_service = MagicMock()
        mock_service.update_agenda = AsyncMock(return_value=updated_agenda)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.patch(
                "/api/v1/agendas/1",
                headers=auth_headers,
                json={"title": "Updated Title"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_agenda(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting an agenda."""
        mock_service = MagicMock()
        mock_service.delete_agenda = AsyncMock(return_value=True)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.delete(
                "/api/v1/agendas/1",
                headers=auth_headers,
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_reorder_agendas(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_agenda,
    ):
        """Test reordering agendas."""
        mock_agenda.questions = []
        mock_agenda.meeting_id = 1

        mock_service = MagicMock()
        mock_service.get_agenda_or_raise = AsyncMock(return_value=mock_agenda)
        mock_service.reorder_agendas = AsyncMock(return_value=2)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.post(
                "/api/v1/agendas/1/reorder",
                headers=auth_headers,
                json={
                    "items": [
                        {"id": 1, "order_num": 1},
                        {"id": 2, "order_num": 0},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["updated_count"] == 2


class TestQuestionsRouter:
    """Tests for questions API endpoints."""

    @pytest.mark.asyncio
    async def test_add_question(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_question,
    ):
        """Test adding a question to an agenda."""
        mock_service = MagicMock()
        mock_service.add_question = AsyncMock(return_value=mock_question)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.post(
                "/api/v1/agendas/1/questions",
                headers=auth_headers,
                json={
                    "question": "What is the budget?",
                    "is_generated": False,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["question"] == "What is the budget?"

    @pytest.mark.asyncio
    async def test_update_question(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_question,
    ):
        """Test updating a question."""
        updated_question = mock_question
        updated_question.answered = True

        mock_service = MagicMock()
        mock_service.update_question = AsyncMock(return_value=updated_question)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.patch(
                "/api/v1/questions/1",
                headers=auth_headers,
                json={"answered": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["answered"] is True

    @pytest.mark.asyncio
    async def test_delete_question(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting a question."""
        mock_service = MagicMock()
        mock_service.delete_question = AsyncMock(return_value=True)

        with patch("app.routers.agendas.AgendaService", return_value=mock_service):
            response = await client.delete(
                "/api/v1/questions/1",
                headers=auth_headers,
            )

        assert response.status_code == 204
