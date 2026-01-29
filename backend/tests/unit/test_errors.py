"""Tests for error handling module."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError


class TestAppException:
    """Test custom AppException class."""

    def test_app_exception_basic(self):
        """Test basic AppException creation."""
        from app.errors import AppException

        exc = AppException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Invalid input",
        )

        assert exc.status_code == 400
        assert exc.code == "VALIDATION_ERROR"
        assert exc.message == "Invalid input"

    def test_app_exception_with_details(self):
        """Test AppException with details."""
        from app.errors import AppException

        details = [{"field": "email", "message": "Invalid email format"}]
        exc = AppException(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Validation failed",
            details=details,
        )

        assert exc.details == details

    def test_app_exception_with_request_id(self):
        """Test AppException with request_id."""
        from app.errors import AppException

        exc = AppException(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Something went wrong",
            request_id="abc-123",
        )

        assert exc.request_id == "abc-123"


class TestErrorResponse:
    """Test error response format."""

    def test_error_response_format(self):
        """Test that error response matches spec format."""
        from app.errors import ErrorResponse, ErrorDetail

        error = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Validation failed",
            details=[{"field": "title", "message": "Required"}],
            request_id="550e8400-e29b-41d4-a716-446655440000",
        )
        response = ErrorResponse(error=error)

        # Convert to dict to check structure
        data = response.model_dump()

        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Validation failed"
        assert data["error"]["details"] == [{"field": "title", "message": "Required"}]
        assert data["error"]["request_id"] == "550e8400-e29b-41d4-a716-446655440000"


class TestExceptionHandlers:
    """Test exception handlers."""

    def test_app_exception_handler(self):
        """Test that AppException is properly handled."""
        from app.errors import AppException, register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        async def test_route():
            raise AppException(
                status_code=400,
                code="TEST_ERROR",
                message="Test error message",
            )

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "Test error message"

    def test_http_exception_handler(self):
        """Test that HTTPException is properly handled."""
        from app.errors import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        async def test_route():
            raise HTTPException(status_code=404, detail="Not found")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"

    def test_validation_error_handler(self):
        """Test that Pydantic ValidationError is properly handled."""
        from app.errors import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        class TestModel(BaseModel):
            name: str
            age: int

        @app.post("/test")
        async def test_route(data: TestModel):
            return data

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/test", json={"name": 123})  # Missing age, wrong type

        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_generic_exception_handler(self):
        """Test that generic exceptions return 500."""
        from app.errors import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        async def test_route():
            raise ValueError("Unexpected error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INTERNAL_ERROR"


class TestErrorCodes:
    """Test standard error codes."""

    def test_standard_error_codes_exist(self):
        """Test that standard error codes are defined."""
        from app.errors import ErrorCode

        assert hasattr(ErrorCode, "VALIDATION_ERROR")
        assert hasattr(ErrorCode, "NOT_FOUND")
        assert hasattr(ErrorCode, "UNAUTHORIZED")
        assert hasattr(ErrorCode, "FORBIDDEN")
        assert hasattr(ErrorCode, "INTERNAL_ERROR")
        assert hasattr(ErrorCode, "RATE_LIMIT_EXCEEDED")
