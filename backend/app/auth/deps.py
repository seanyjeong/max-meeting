"""FastAPI dependency injection for authentication."""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .jwt import verify_token


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """Dependency to get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token, token_type="access")
    return payload


async def verify_refresh_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """Dependency to verify refresh token."""
    token = credentials.credentials
    payload = verify_token(token, token_type="refresh")
    return payload
