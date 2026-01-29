"""Tests for FastAPI main application."""
import pytest
from fastapi.testclient import TestClient


class TestAppCreation:
    """Test FastAPI app creation."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        from app.main import create_app
        from fastapi import FastAPI

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_has_api_version_prefix(self):
        """Test that API routes have version prefix."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app)

        # Health check should be at /api/v1/health
        response = client.get("/api/v1/health")
        assert response.status_code == 200


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_returns_ok(self):
        """Test that health check returns OK status."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_check_returns_version(self):
        """Test that health check returns API version."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health")

        data = response.json()
        assert "version" in data


class TestCORS:
    """Test CORS middleware configuration."""

    def test_cors_allows_configured_origins(self):
        """Test that CORS allows configured origins."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should allow the origin
        assert response.headers.get("access-control-allow-origin") in [
            "http://localhost:5173",
            "*",
        ]


class TestRequestId:
    """Test request ID middleware."""

    def test_response_has_request_id_header(self):
        """Test that responses include X-Request-ID header."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health")

        assert "x-request-id" in response.headers


class TestErrorHandling:
    """Test that error handlers are registered."""

    def test_404_returns_structured_error(self):
        """Test that 404 returns structured error response."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]


class TestAuthRouterRegistration:
    """Test that auth router is registered."""

    def test_auth_login_endpoint_exists(self):
        """Test that /api/v1/auth/login endpoint exists."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        # Should return 422 (validation error) not 404
        response = client.post("/api/v1/auth/login", json={})

        # 422 means endpoint exists but validation failed
        # 404 means endpoint doesn't exist
        assert response.status_code != 404

    def test_auth_me_endpoint_exists(self):
        """Test that /api/v1/auth/me endpoint exists."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/auth/me")

        # Should return 401/403 (auth required) not 404
        assert response.status_code != 404


class TestAppMetadata:
    """Test app metadata configuration."""

    def test_app_has_title(self):
        """Test that app has a title."""
        from app.main import create_app

        app = create_app()
        assert app.title is not None
        assert len(app.title) > 0

    def test_app_has_version(self):
        """Test that app has a version."""
        from app.main import create_app

        app = create_app()
        assert app.version is not None
