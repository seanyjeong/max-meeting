"""Tests for application configuration.

Based on Section 13 of the MAX Meeting specification.
"""
import pytest
from app.config import Settings, get_settings


class TestBasicSettings:
    """Test basic application settings."""

    def test_settings_has_defaults(self):
        """Test that settings have sensible defaults."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )

        assert settings.APP_ENV == "development"
        assert settings.DEBUG is False
        assert settings.API_VERSION == "v1"

    def test_secret_key_min_length(self):
        """Test that SECRET_KEY requires minimum 32 bytes."""
        with pytest.raises(ValueError):
            Settings(
                SECRET_KEY="short",
                AUTH_PASSWORD_HASH="test",
                JWT_SECRET="test-jwt-secret-at-least-32-bytes"
            )

    def test_jwt_secret_min_length(self):
        """Test that JWT_SECRET requires minimum 32 bytes."""
        with pytest.raises(ValueError):
            Settings(
                SECRET_KEY="test-secret-key-at-least-32-bytes",
                AUTH_PASSWORD_HASH="test",
                JWT_SECRET="short"
            )


class TestDatabaseSettings:
    """Test database configuration."""

    def test_database_url_default(self):
        """Test database URL has default."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert "postgresql" in settings.DATABASE_URL

    def test_async_database_url_conversion(self):
        """Test that sync URL is converted to async URL."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes",
            DATABASE_URL="postgresql://user:pass@localhost/db"
        )
        assert settings.ASYNC_DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"

    def test_postgres_url_conversion(self):
        """Test that postgres:// URL is also converted."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes",
            DATABASE_URL="postgres://user:pass@localhost/db"
        )
        assert settings.ASYNC_DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"

    def test_db_pool_settings(self):
        """Test DB pool configuration defaults."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert settings.DB_POOL_SIZE == 5
        assert settings.DB_MAX_OVERFLOW == 10
        assert settings.DB_POOL_TIMEOUT == 30


class TestStorageSettings:
    """Test file storage configuration."""

    def test_storage_defaults(self):
        """Test storage configuration defaults."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert settings.STORAGE_BACKEND == "local"
        # STORAGE_PATH may be overridden by .env file, so just check it's set
        assert settings.STORAGE_PATH is not None
        assert len(settings.STORAGE_PATH) > 0
        # RECORDINGS_PATH may also be overridden
        assert settings.RECORDINGS_PATH is not None
        assert len(settings.RECORDINGS_PATH) > 0
        assert settings.MAX_UPLOAD_SIZE_MB == 500

    def test_max_upload_size_bytes(self):
        """Test max upload size conversion to bytes."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes",
            MAX_UPLOAD_SIZE_MB=100
        )
        assert settings.MAX_UPLOAD_SIZE_BYTES == 100 * 1024 * 1024


class TestCelerySettings:
    """Test Celery configuration."""

    def test_celery_defaults(self):
        """Test Celery configuration defaults."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert settings.CELERY_TASK_TIME_LIMIT == 7200
        assert settings.CELERY_TASK_SOFT_TIME_LIMIT == 6900
        assert settings.CELERY_WORKER_CONCURRENCY == 1
        assert settings.CELERY_TASK_ACKS_LATE is True


class TestSTTSettings:
    """Test STT configuration."""

    def test_stt_defaults(self):
        """Test STT configuration defaults."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert settings.WHISPER_MODEL == "medium"
        assert settings.WHISPER_DEVICE == "cpu"
        assert settings.STT_CHUNK_MINUTES == 10
        assert settings.STT_MAX_PARALLEL == 4


class TestLLMSettings:
    """Test LLM configuration."""

    def test_llm_defaults(self):
        """Test LLM configuration defaults."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert settings.LLM_PROVIDER == "gemini"
        assert settings.LLM_MAX_TOKENS_PER_REQUEST == 100000


class TestCORSSettings:
    """Test CORS configuration."""

    def test_cors_origins_default(self):
        """Test CORS origins have sensible defaults."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0

    def test_cors_origins_from_json_string(self):
        """Test CORS origins can be parsed from JSON string."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes",
            CORS_ORIGINS='["https://example.com", "https://app.example.com"]'
        )
        assert settings.CORS_ORIGINS == ["https://example.com", "https://app.example.com"]

    def test_cors_origins_from_comma_separated(self):
        """Test CORS origins can be parsed from comma-separated string."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes",
            CORS_ORIGINS="https://example.com, https://app.example.com"
        )
        assert settings.CORS_ORIGINS == ["https://example.com", "https://app.example.com"]


class TestRateLimitSettings:
    """Test rate limit configuration."""

    def test_rate_limit_defaults(self):
        """Test rate limit defaults per Section 8 of spec."""
        settings = Settings(
            SECRET_KEY="test-secret-key-at-least-32-bytes",
            AUTH_PASSWORD_HASH="test",
            JWT_SECRET="test-jwt-secret-at-least-32-bytes"
        )
        assert settings.RATE_LIMIT_LOGIN == "5/minute"
        assert settings.RATE_LIMIT_REFRESH == "10/minute"
        assert settings.RATE_LIMIT_UPLOAD == "10/hour"
        assert settings.RATE_LIMIT_LLM == "30/hour"
        assert settings.RATE_LIMIT_DEFAULT == "200/minute"


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
