"""Pytest configuration and fixtures."""

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def mock_settings_env():
    """Set up test environment variables."""
    os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-bytes-long")
    os.environ.setdefault("AUTH_PASSWORD_HASH", "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU0vO3rO0hCi")  # "testpassword123"
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-at-least-32-bytes-long")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    os.environ.setdefault("JWT_ACCESS_EXPIRE_MINUTES", "60")
    os.environ.setdefault("JWT_REFRESH_EXPIRE_DAYS", "7")
    os.environ.setdefault("JWT_AUDIENCE", "max-meeting")
    os.environ.setdefault("JWT_ISSUER", "max-meeting-api")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    # Use temp directory for storage in tests
    os.environ.setdefault("STORAGE_PATH", "/tmp/max-meeting-test")
    os.environ.setdefault("RECORDINGS_PATH", "/tmp/max-meeting-test/recordings")

    yield

    # Clear cache after test
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.JWT_SECRET = "test-secret-key-at-least-32-bytes-long"
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_ACCESS_EXPIRE_MINUTES = 60
    settings.JWT_REFRESH_EXPIRE_DAYS = 7
    settings.JWT_AUDIENCE = "max-meeting"
    settings.JWT_ISSUER = "max-meeting-api"
    settings.AUTH_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU0vO3rO0hCi"
    settings.RATE_LIMIT_LOGIN = "5/minute"
    settings.RATE_LIMIT_REFRESH = "10/minute"
    settings.RATE_LIMIT_DEFAULT = "200/minute"
    return settings


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create mock authentication headers for API tests."""
    from app.auth import create_access_token

    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}"}


def create_mock_db_session():
    """Create a mock database session."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = MagicMock()
    return mock_session


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    from app.main import create_app
    from app.database import get_db

    app = create_app()

    # Mock Redis
    app.state.redis = AsyncMock()

    # Override DB dependency with mock session
    mock_db = create_mock_db_session()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
