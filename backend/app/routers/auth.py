"""Authentication API endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.auth import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_current_user,
)
from app.auth.deps import verify_refresh_token
from app.config import get_settings
from app.middleware.rate_limit import create_rate_limit_dependency


router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


class LoginRequest(BaseModel):
    """Login request."""
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Current user response."""
    user_id: str
    token_type: str
    expires_at: int


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    _rate_limit: Annotated[None, Depends(create_rate_limit_dependency(settings.RATE_LIMIT_LOGIN))] = None,
):
    """Login endpoint. Rate limit: 5 requests per minute per IP."""
    if not verify_password(credentials.password, settings.AUTH_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = "1"

    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    payload: Annotated[dict, Depends(verify_refresh_token)],
    _rate_limit: Annotated[None, Depends(create_rate_limit_dependency(settings.RATE_LIMIT_REFRESH))] = None,
):
    """Refresh access token. Rate limit: 10 requests per minute per IP."""
    user_id = payload["sub"]

    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Logout endpoint."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get current user information."""
    return UserResponse(
        user_id=current_user["sub"],
        token_type=current_user.get("type", "access"),
        expires_at=current_user["exp"],
    )
