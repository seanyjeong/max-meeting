"""Integration test specific configuration.

Integration tests require a real database connection.
They are skipped when the database is not available.
"""

import os
import socket

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient


def is_db_available() -> bool:
    """Check if database is available for integration tests."""
    # Always skip integration tests in CI/test environments
    # unless explicitly enabled
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
        return False

    # Try to connect to the database
    try:
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = int(os.environ.get("DB_PORT", "5432"))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((db_host, db_port))
        sock.close()
        return result == 0
    except Exception:
        return False


# Skip all integration tests if DB is not available
pytestmark = pytest.mark.skipif(
    not is_db_available(),
    reason="Integration tests require RUN_INTEGRATION_TESTS=1 and database available"
)


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for integration testing with real DB."""
    from app.main import create_app

    app = create_app()

    # Mock Redis (still needed)
    app.state.redis = AsyncMock()

    # Use real database connection (no dependency override)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
