"""Tests for database module."""
import pytest
from unittest.mock import patch, MagicMock


class TestAsyncEngine:
    """Test async database engine creation."""

    def test_get_async_engine_returns_engine(self):
        """Test that get_async_engine returns an engine object."""
        from app.database import get_async_engine

        # Clear cache to ensure fresh engine
        get_async_engine.cache_clear()

        engine = get_async_engine()

        assert engine is not None
        # Should have typical engine attributes
        assert hasattr(engine, "url")

    def test_get_async_engine_uses_async_url(self):
        """Test that engine uses async database URL."""
        from app.database import get_async_engine

        get_async_engine.cache_clear()
        engine = get_async_engine()

        # The URL should contain asyncpg driver
        url_str = str(engine.url)
        assert "asyncpg" in url_str

    def test_get_async_engine_is_cached(self):
        """Test that engine is cached (same instance returned)."""
        from app.database import get_async_engine

        get_async_engine.cache_clear()

        engine1 = get_async_engine()
        engine2 = get_async_engine()

        assert engine1 is engine2


class TestAsyncSessionMaker:
    """Test async session maker."""

    def test_get_async_session_maker_exists(self):
        """Test that get_async_session_maker is available."""
        from app.database import get_async_session_maker

        session_maker = get_async_session_maker()
        assert session_maker is not None

    def test_get_async_session_maker_is_configured(self):
        """Test that async_sessionmaker is properly configured."""
        from app.database import get_async_session_maker
        from sqlalchemy.ext.asyncio import AsyncSession

        session_maker = get_async_session_maker()

        # Check that the session class is AsyncSession
        assert session_maker.class_ == AsyncSession


class TestGetDbDependency:
    """Test get_db dependency function."""

    @pytest.mark.asyncio
    async def test_get_db_is_async_generator(self):
        """Test that get_db is an async generator."""
        from app.database import get_db
        import inspect

        assert inspect.isasyncgenfunction(get_db)


class TestDatabaseModule:
    """Test database module exports."""

    def test_module_exports(self):
        """Test that database module exports required objects."""
        from app import database

        assert hasattr(database, "get_async_engine")
        assert hasattr(database, "get_async_session_maker")
        assert hasattr(database, "get_db")
        assert hasattr(database, "Base")

    def test_base_is_declarative(self):
        """Test that Base is a proper declarative base."""
        from app.database import Base
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)
