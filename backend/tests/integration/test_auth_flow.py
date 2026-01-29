"""Integration tests for authentication flow."""

import os
import pytest
from httpx import AsyncClient

# Skip all tests in this file unless integration tests are explicitly enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"),
    reason="Integration tests require RUN_INTEGRATION_TESTS=1"
)


class TestAuthFlow:
    """Test complete authentication flow."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """Test successful login returns tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "wrongpassword"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_access_protected_route_without_token(self, client: AsyncClient):
        """Test accessing protected route without token fails."""
        response = await client.get("/api/v1/meetings")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_token(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test accessing protected route with valid token succeeds."""
        response = await client.get("/api/v1/meetings", headers=auth_headers)

        # Should succeed (may return empty list)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient):
        """Test token refresh flow."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"password": "testpassword123"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()

        # Then refresh
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token fails."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401
