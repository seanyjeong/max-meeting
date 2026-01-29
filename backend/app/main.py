"""
MAX Meeting FastAPI Application.

Main entry point for the backend API.
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis as AsyncRedis
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import get_settings
from app.errors import register_exception_handlers
from app.routers import agendas, auth, contacts, meeting_types, meetings, notes, recordings, results, search, sketches


settings = get_settings()

# Initialize Sentry for error tracking
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        send_default_pii=False,  # Don't send PII to Sentry
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    redis_url = settings.REDIS_URL
    if settings.REDIS_PASSWORD:
        # Add password to URL if not already present
        if "@" not in redis_url:
            redis_url = redis_url.replace("redis://", f"redis://:{settings.REDIS_PASSWORD}@")

    app.state.redis = AsyncRedis.from_url(redis_url, decode_responses=True)

    yield

    # Shutdown
    await app.state.redis.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MAX Meeting API",
        description="Meeting management SaaS - record, transcribe, and summarize meetings",
        version="1.0.0",
        docs_url=f"/api/{settings.API_VERSION}/docs",
        redoc_url=f"/api/{settings.API_VERSION}/redoc",
        openapi_url=f"/api/{settings.API_VERSION}/openapi.json",
        lifespan=lifespan,
    )

    # Register CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add request ID to all requests."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response

    # Register security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Register exception handlers
    register_exception_handlers(app)

    # Create API router with version prefix
    api_prefix = f"/api/{settings.API_VERSION}"

    # Register routers
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(contacts.router, prefix=api_prefix)
    app.include_router(meeting_types.router, prefix=api_prefix)
    app.include_router(meetings.router, prefix=api_prefix)
    app.include_router(agendas.router, prefix=api_prefix)
    app.include_router(notes.router, prefix=api_prefix)
    app.include_router(recordings.router, prefix=api_prefix)
    app.include_router(results.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(sketches.router, prefix=api_prefix)

    # Health check endpoint
    @app.get(f"{api_prefix}/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "version": app.version,
            "api_version": settings.API_VERSION,
        }

    return app


# Create app instance for uvicorn
app = create_app()
