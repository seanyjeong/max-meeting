"""
Application configuration using Pydantic Settings.

Based on Section 13 of the MAX Meeting specification.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ============================================
    # Basic Settings
    # ============================================
    APP_ENV: Literal["development", "production", "test"] = Field(
        default="development",
    )
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(..., min_length=32)
    API_VERSION: str = Field(default="v1")

    # ============================================
    # Authentication
    # ============================================
    AUTH_PASSWORD_HASH: str = Field(...)
    JWT_SECRET: str = Field(..., min_length=32)
    JWT_ACCESS_EXPIRE_MINUTES: int = Field(default=60)
    JWT_REFRESH_EXPIRE_DAYS: int = Field(default=7)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ISSUER: str = Field(default="max-meeting-api")
    JWT_AUDIENCE: str = Field(default="max-meeting")

    # ============================================
    # Database
    # ============================================
    DATABASE_URL: str = Field(default="postgresql://localhost/maxmeeting")
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_POOL_TIMEOUT: int = Field(default=30)

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Convert sync URL to async URL for asyncpg."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # ============================================
    # Redis
    # ============================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: str = Field(default="")

    # ============================================
    # Celery
    # ============================================
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0")
    CELERY_TASK_TIME_LIMIT: int = Field(default=7200)
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(default=6900)
    CELERY_WORKER_CONCURRENCY: int = Field(default=1)
    CELERY_TASK_ACKS_LATE: bool = Field(default=True)

    # ============================================
    # File Storage
    # ============================================
    STORAGE_BACKEND: Literal["local", "s3"] = Field(default="local")
    STORAGE_PATH: str = Field(default="/data/max-meeting")
    RECORDINGS_PATH: str = Field(default="/data/max-meeting/recordings")
    MAX_UPLOAD_SIZE_MB: int = Field(default=500)
    STORAGE_ENCRYPTION_KEY: str = Field(default="")

    @property
    def MAX_UPLOAD_SIZE_BYTES(self) -> int:
        """Get max upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ============================================
    # STT
    # ============================================
    WHISPER_MODEL: str = Field(default="medium")
    WHISPER_DEVICE: Literal["cpu", "cuda"] = Field(default="cpu")
    STT_CHUNK_MINUTES: int = Field(default=10)
    STT_MAX_PARALLEL: int = Field(default=4)
    HUGGINGFACE_TOKEN: str = Field(default="")  # Required for pyannote speaker diarization

    # ============================================
    # LLM
    # ============================================
    LLM_PROVIDER: Literal["gemini", "openai"] = Field(default="gemini")
    GEMINI_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    LLM_MAX_TOKENS_PER_REQUEST: int = Field(default=100000)

    # ============================================
    # Monitoring
    # ============================================
    SENTRY_DSN: str = Field(default="")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    LOG_FORMAT: Literal["json", "text"] = Field(default="json")

    # ============================================
    # Backup
    # ============================================
    BACKUP_ENABLED: bool = Field(default=True)
    BACKUP_HOST: str = Field(default="192.168.35.249")
    BACKUP_USER: str = Field(default="sean")
    BACKUP_PATH: str = Field(default="/backup/max-meeting")
    BACKUP_INTERVAL_HOURS: int = Field(default=1)
    BACKUP_GPG_RECIPIENT: str = Field(default="")

    # ============================================
    # Rate Limiting
    # ============================================
    RATE_LIMIT_LOGIN: str = Field(default="5/minute")
    RATE_LIMIT_REFRESH: str = Field(default="10/minute")
    RATE_LIMIT_UPLOAD: str = Field(default="10/hour")
    RATE_LIMIT_LLM: str = Field(default="30/hour")
    RATE_LIMIT_DEFAULT: str = Field(default="200/minute")

    # ============================================
    # Security / CORS
    # ============================================
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )
    ALLOWED_HOSTS: list[str] = Field(
        default=["localhost", "meeting.etlab.kr"]
    )

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated string or JSON list to list."""
        if isinstance(v, str):
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ============================================
    # PII Encryption
    # ============================================
    PII_ENCRYPTION_KEY: str = Field(default="")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
