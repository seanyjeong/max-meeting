"""Unit tests for authentication module."""
import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from jose import jwt


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test that password hashing and verification works."""
        from app.auth.password import verify_password, get_password_hash

        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert verify_password(password, hashed)

    def test_password_hash_is_different_each_time(self):
        """Test that the same password produces different hashes."""
        from app.auth.password import get_password_hash

        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Salt should make hashes different

    def test_wrong_password_fails_verification(self):
        """Test that wrong password fails verification."""
        from app.auth.password import verify_password, get_password_hash

        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert not verify_password(wrong_password, hashed)

    def test_empty_password_can_be_hashed(self):
        """Test that empty password can be hashed."""
        from app.auth.password import verify_password, get_password_hash

        password = ""
        hashed = get_password_hash(password)

        assert verify_password(password, hashed)

    def test_unicode_password(self):
        """Test that unicode passwords work correctly."""
        from app.auth.password import verify_password, get_password_hash

        password = "한글비밀번호123!@#"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed)

    def test_long_password(self):
        """Test that long passwords work correctly."""
        from app.auth.password import verify_password, get_password_hash

        # bcrypt has a 72-byte limit, test near boundary
        password = "a" * 72
        hashed = get_password_hash(password)

        assert verify_password(password, hashed)

    def test_bcrypt_cost_factor(self):
        """Test that bcrypt uses cost factor 12."""
        from app.auth.password import get_password_hash

        hashed = get_password_hash("test")
        # bcrypt hash format: $2b$12$... where 12 is the cost factor
        assert "$2b$12$" in hashed


class TestJWTTokenCreation:
    """Test JWT token creation."""

    def test_create_access_token(self):
        """Test access token creation."""
        from app.auth.jwt import create_access_token
        from app.config import get_settings

        settings = get_settings()

        token = create_access_token(subject="user123")
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )

        assert payload["sub"] == "user123"
        assert payload["type"] == "access"
        assert payload["aud"] == settings.JWT_AUDIENCE
        assert payload["iss"] == settings.JWT_ISSUER
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        from app.auth.jwt import create_refresh_token
        from app.config import get_settings

        settings = get_settings()

        token = create_refresh_token(subject="user123")
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )

        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert payload["aud"] == settings.JWT_AUDIENCE
        assert payload["iss"] == settings.JWT_ISSUER

    def test_access_token_expiry(self):
        """Test that access token has correct expiry."""
        from app.auth.jwt import create_access_token
        from app.config import get_settings

        settings = get_settings()

        token = create_access_token(subject="user123")
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )

        now = datetime.now(timezone.utc)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = now + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)

        # Allow 5 seconds tolerance
        assert abs((exp - expected_exp).total_seconds()) < 5

    def test_refresh_token_expiry(self):
        """Test that refresh token has correct expiry."""
        from app.auth.jwt import create_refresh_token
        from app.config import get_settings

        settings = get_settings()

        token = create_refresh_token(subject="user123")
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )

        now = datetime.now(timezone.utc)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)

        # Allow 5 seconds tolerance
        assert abs((exp - expected_exp).total_seconds()) < 5

    def test_access_token_with_additional_claims(self):
        """Test access token with additional claims."""
        from app.auth.jwt import create_access_token
        from app.config import get_settings

        settings = get_settings()
        additional_claims = {"role": "admin", "permissions": ["read", "write"]}

        token = create_access_token(subject="user123", additional_claims=additional_claims)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )

        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    def test_unique_jti_per_token(self):
        """Test that each token has a unique JTI."""
        from app.auth.jwt import create_access_token
        from app.config import get_settings

        settings = get_settings()

        token1 = create_access_token(subject="user123")
        token2 = create_access_token(subject="user123")

        payload1 = jwt.decode(
            token1,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )
        payload2 = jwt.decode(
            token2,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
        )

        assert payload1["jti"] != payload2["jti"]


class TestJWTTokenVerification:
    """Test JWT token verification."""

    def test_verify_valid_access_token(self):
        """Test verification of valid access token."""
        from app.auth.jwt import create_access_token, verify_token

        token = create_access_token(subject="user123")
        payload = verify_token(token, token_type="access")

        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_verify_valid_refresh_token(self):
        """Test verification of valid refresh token."""
        from app.auth.jwt import create_refresh_token, verify_token

        token = create_refresh_token(subject="user123")
        payload = verify_token(token, token_type="refresh")

        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_verify_access_token_as_refresh_fails(self):
        """Test that access token cannot be used as refresh token."""
        from app.auth.jwt import create_access_token, verify_token

        token = create_access_token(subject="user123")

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="refresh")

        assert exc_info.value.status_code == 401

    def test_verify_refresh_token_as_access_fails(self):
        """Test that refresh token cannot be used as access token."""
        from app.auth.jwt import create_refresh_token, verify_token

        token = create_refresh_token(subject="user123")

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_invalid_token_fails(self):
        """Test that invalid token fails verification."""
        from app.auth.jwt import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here", token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_expired_token_fails(self):
        """Test that expired token fails verification."""
        from app.auth.jwt import verify_token
        from app.config import get_settings

        settings = get_settings()

        # Create an expired token manually
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=2)

        claims = {
            "sub": "user123",
            "iat": past,
            "exp": past + timedelta(minutes=1),  # Already expired
            "jti": "test-jti",
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
            "type": "access",
        }

        token = jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_token_wrong_audience_fails(self):
        """Test that token with wrong audience fails."""
        from app.auth.jwt import verify_token
        from app.config import get_settings

        settings = get_settings()

        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user123",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": "test-jti",
            "aud": "wrong-audience",
            "iss": settings.JWT_ISSUER,
            "type": "access",
        }

        token = jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_token_wrong_issuer_fails(self):
        """Test that token with wrong issuer fails."""
        from app.auth.jwt import verify_token
        from app.config import get_settings

        settings = get_settings()

        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user123",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": "test-jti",
            "aud": settings.JWT_AUDIENCE,
            "iss": "wrong-issuer",
            "type": "access",
        }

        token = jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_token_missing_subject_fails(self):
        """Test that token without subject fails."""
        from app.auth.jwt import verify_token
        from app.config import get_settings

        settings = get_settings()

        now = datetime.now(timezone.utc)
        claims = {
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": "test-jti",
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
            "type": "access",
        }

        token = jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_token_wrong_secret_fails(self):
        """Test that token signed with wrong secret fails."""
        from app.auth.jwt import verify_token
        from app.config import get_settings

        settings = get_settings()

        now = datetime.now(timezone.utc)
        claims = {
            "sub": "user123",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": "test-jti",
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
            "type": "access",
        }

        token = jwt.encode(claims, "wrong-secret-key", algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="access")

        assert exc_info.value.status_code == 401


class TestRateLimitParsing:
    """Test rate limit string parsing."""

    def test_parse_rate_limit_per_minute(self):
        """Test parsing rate limit per minute."""
        from app.middleware.rate_limit import parse_rate_limit

        limit, window = parse_rate_limit("5/minute")
        assert limit == 5
        assert window == 60

    def test_parse_rate_limit_per_second(self):
        """Test parsing rate limit per second."""
        from app.middleware.rate_limit import parse_rate_limit

        limit, window = parse_rate_limit("100/second")
        assert limit == 100
        assert window == 1

    def test_parse_rate_limit_per_hour(self):
        """Test parsing rate limit per hour."""
        from app.middleware.rate_limit import parse_rate_limit

        limit, window = parse_rate_limit("10/hour")
        assert limit == 10
        assert window == 3600

    def test_parse_rate_limit_per_day(self):
        """Test parsing rate limit per day."""
        from app.middleware.rate_limit import parse_rate_limit

        limit, window = parse_rate_limit("1000/day")
        assert limit == 1000
        assert window == 86400


class TestRateLimiter:
    """Test rate limiter functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = MagicMock()
        redis.zremrangebyscore = MagicMock(return_value=None)
        redis.zcard = MagicMock(return_value=0)
        redis.zadd = MagicMock(return_value=1)
        redis.expire = MagicMock(return_value=True)
        return redis

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self, mock_redis):
        """Test that rate limiter allows requests within limit."""
        from app.middleware.rate_limit import RateLimiter

        # Make mock awaitable
        async def async_return(value):
            return value

        mock_redis.zremrangebyscore = MagicMock(side_effect=lambda *args: async_return(None))
        mock_redis.zcard = MagicMock(side_effect=lambda *args: async_return(2))  # 2 requests so far
        mock_redis.zadd = MagicMock(side_effect=lambda *args, **kwargs: async_return(1))
        mock_redis.expire = MagicMock(side_effect=lambda *args: async_return(True))

        limiter = RateLimiter(mock_redis)
        allowed, info = await limiter.check_rate_limit("test:key", limit=5, window_seconds=60)

        assert allowed is True
        assert info["limit"] == 5
        assert info["remaining"] == 2  # 5 - 2 - 1 = 2

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self, mock_redis):
        """Test that rate limiter blocks requests over limit."""
        from app.middleware.rate_limit import RateLimiter

        async def async_return(value):
            return value

        mock_redis.zremrangebyscore = MagicMock(side_effect=lambda *args: async_return(None))
        mock_redis.zcard = MagicMock(side_effect=lambda *args: async_return(5))  # At limit
        mock_redis.zadd = MagicMock(side_effect=lambda *args, **kwargs: async_return(1))
        mock_redis.expire = MagicMock(side_effect=lambda *args: async_return(True))

        limiter = RateLimiter(mock_redis)
        allowed, info = await limiter.check_rate_limit("test:key", limit=5, window_seconds=60)

        assert allowed is False
        assert info["remaining"] == 0


class TestAuthDependencies:
    """Test authentication dependencies."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test get_current_user with valid token."""
        from app.auth.deps import get_current_user
        from app.auth.jwt import create_access_token
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(subject="user123")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials)

        assert user["sub"] == "user123"
        assert user["type"] == "access"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        from app.auth.deps import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_refresh_token_valid(self):
        """Test verify_refresh_token with valid refresh token."""
        from app.auth.deps import verify_refresh_token
        from app.auth.jwt import create_refresh_token
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_refresh_token(subject="user123")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        payload = await verify_refresh_token(credentials)

        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    @pytest.mark.asyncio
    async def test_verify_refresh_token_with_access_token_fails(self):
        """Test verify_refresh_token fails with access token."""
        from app.auth.deps import verify_refresh_token
        from app.auth.jwt import create_access_token
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(subject="user123")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await verify_refresh_token(credentials)

        assert exc_info.value.status_code == 401


class TestConfigSettings:
    """Test configuration settings."""

    def test_jwt_settings_loaded(self):
        """Test that JWT settings are loaded correctly."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.JWT_SECRET is not None
        assert len(settings.JWT_SECRET) >= 32
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_ACCESS_EXPIRE_MINUTES == 60
        assert settings.JWT_REFRESH_EXPIRE_DAYS == 7
        assert settings.JWT_AUDIENCE == "max-meeting"
        assert settings.JWT_ISSUER == "max-meeting-api"

    def test_rate_limit_settings_loaded(self):
        """Test that rate limit settings are loaded correctly."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.RATE_LIMIT_LOGIN == "5/minute"
        assert settings.RATE_LIMIT_REFRESH == "10/minute"
        assert settings.RATE_LIMIT_DEFAULT == "200/minute"


class TestAuditLogger:
    """Test audit logging functionality."""

    @pytest.mark.asyncio
    async def test_audit_logger_creates_log_entry(self):
        """Test that audit logger creates log entry."""
        from app.middleware.audit_log import AuditLogger
        from unittest.mock import AsyncMock

        mock_db = AsyncMock()
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.state.request_id = "test-request-id"
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "TestClient/1.0"}

        await AuditLogger.log(
            db=mock_db,
            event_type="LOGIN",
            user_id=1,
            action="LOGIN",
            status="SUCCESS",
            request=mock_request,
            resource_type="auth",
            details={"method": "password"},
        )

        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_middleware_adds_request_id(self):
        """Test that audit middleware adds request ID."""
        from app.middleware.audit_log import audit_middleware
        from unittest.mock import AsyncMock

        mock_request = Mock()
        mock_request.state = Mock()

        mock_response = Mock()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await audit_middleware(mock_request, mock_call_next)

        assert hasattr(mock_request.state, "request_id")
        assert "X-Request-ID" in response.headers
