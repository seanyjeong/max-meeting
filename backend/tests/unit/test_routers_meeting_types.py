"""Unit tests for meeting_types router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMeetingTypeSchemas:
    """Test MeetingType schemas."""

    def test_meeting_type_create_schema(self):
        """Test MeetingTypeCreate schema."""
        from app.schemas.meeting_type import MeetingTypeCreate

        # Minimal - just name
        mt = MeetingTypeCreate(name="북부")
        assert mt.name == "북부"
        assert mt.description is None
        assert mt.question_perspective is None

    def test_meeting_type_create_with_perspective(self):
        """Test MeetingTypeCreate with question_perspective."""
        from app.schemas.meeting_type import MeetingTypeCreate

        perspective = "각 지점 원장 입장에서 이 안건이 우리 지점에 어떤 이익이 되는지 관점으로 질문"
        mt = MeetingTypeCreate(
            name="북부",
            description="북부 지역 연합 회의",
            question_perspective=perspective,
        )
        assert mt.name == "북부"
        assert mt.description == "북부 지역 연합 회의"
        assert mt.question_perspective == perspective

    def test_meeting_type_create_requires_name(self):
        """Test that name is required."""
        from app.schemas.meeting_type import MeetingTypeCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            MeetingTypeCreate()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_meeting_type_create_name_length(self):
        """Test name length validation (max 50)."""
        from app.schemas.meeting_type import MeetingTypeCreate
        from pydantic import ValidationError

        # Empty name should fail
        with pytest.raises(ValidationError):
            MeetingTypeCreate(name="")

        # Name too long should fail (>50 chars)
        with pytest.raises(ValidationError):
            MeetingTypeCreate(name="a" * 51)

        # 50 chars should be valid
        mt = MeetingTypeCreate(name="a" * 50)
        assert len(mt.name) == 50

    def test_meeting_type_update_all_optional(self):
        """Test that MeetingTypeUpdate has all optional fields."""
        from app.schemas.meeting_type import MeetingTypeUpdate

        # Empty update should be valid
        update = MeetingTypeUpdate()
        assert update.model_dump(exclude_unset=True) == {}

        # Partial update should be valid
        update = MeetingTypeUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.question_perspective is None

    def test_meeting_type_update_perspective(self):
        """Test updating only question_perspective."""
        from app.schemas.meeting_type import MeetingTypeUpdate

        perspective = "새로운 질문 관점"
        update = MeetingTypeUpdate(question_perspective=perspective)

        assert update.name is None
        assert update.question_perspective == perspective
        assert "question_perspective" in update.model_fields_set

    def test_meeting_type_update_clear_perspective(self):
        """Test clearing question_perspective to null."""
        from app.schemas.meeting_type import MeetingTypeUpdate

        # Explicitly set to None to clear
        update = MeetingTypeUpdate(question_perspective=None)

        # Should be in model_fields_set (explicitly provided)
        assert "question_perspective" in update.model_fields_set
        assert update.question_perspective is None

    def test_meeting_type_response_schema(self):
        """Test MeetingTypeResponse schema."""
        from app.schemas.meeting_type import MeetingTypeResponse

        response = MeetingTypeResponse(
            id=1,
            name="북부",
            description="북부 지역",
            question_perspective="비용 관점",
        )
        assert response.id == 1
        assert response.name == "북부"
        assert response.description == "북부 지역"
        assert response.question_perspective == "비용 관점"

    def test_meeting_type_response_nullable_fields(self):
        """Test MeetingTypeResponse with null optional fields."""
        from app.schemas.meeting_type import MeetingTypeResponse

        response = MeetingTypeResponse(
            id=1,
            name="일산",
        )
        assert response.id == 1
        assert response.name == "일산"
        assert response.description is None
        assert response.question_perspective is None


class TestLLMServiceQuestionPerspective:
    """Test LLM service with question_perspective."""

    def test_generate_questions_signature(self):
        """Test generate_questions accepts question_perspective parameter."""
        import inspect
        from app.services.llm import LLMService

        sig = inspect.signature(LLMService.generate_questions)
        params = list(sig.parameters.keys())

        assert "question_perspective" in params

    def test_generate_questions_convenience_function_signature(self):
        """Test convenience function accepts question_perspective parameter."""
        import inspect
        from app.services.llm import generate_questions

        sig = inspect.signature(generate_questions)
        params = list(sig.parameters.keys())

        assert "question_perspective" in params


class TestMeetingTypeModel:
    """Test MeetingType model."""

    def test_meeting_type_has_all_required_columns(self):
        """Test MeetingType has all required columns."""
        from app.models.meeting import MeetingType

        columns = [c.name for c in MeetingType.__table__.columns]

        required = ["id", "name", "description", "question_perspective"]
        for col in required:
            assert col in columns, f"Missing column: {col}"

    def test_meeting_type_question_perspective_type(self):
        """Test question_perspective column type."""
        from app.models.meeting import MeetingType
        from sqlalchemy import Text

        column = MeetingType.__table__.columns["question_perspective"]
        assert isinstance(column.type, Text)
