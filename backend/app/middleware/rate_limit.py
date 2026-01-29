"""Rate limiting middleware using Redis."""
import time

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis as AsyncRedis

from app.config import get_settings


settings = get_settings()


class RateLimiter:
    """Rate limiter using Redis sliding window."""

    def __init__(self, redis_client: AsyncRedis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, dict]:
        """Check if request is within rate limit."""
        now = time.time()
        window_start = now - window_seconds

        await self.redis.zremrangebyscore(key, 0, window_start)
        current_count = await self.redis.zcard(key)

        remaining = max(0, limit - current_count)
        reset_time = int(now + window_seconds)

        if current_count >= limit:
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": reset_time
            }

        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, window_seconds)

        return True, {
            "limit": limit,
            "remaining": remaining - 1,
            "reset": reset_time
        }


def parse_rate_limit(rate_string: str) -> tuple[int, int]:
    """Parse rate limit string like '5/minute' to (limit, window_seconds)."""
    limit_str, period = rate_string.split("/")
    limit = int(limit_str)

    period_map = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }

    window_seconds = period_map.get(period.lower(), 60)

    return limit, window_seconds


def create_rate_limit_dependency(rate_string: str):
    """Create a rate limit dependency with a specific rate string."""
    async def dependency(request: Request):
        return await rate_limit_dependency(request, rate_string)
    return dependency


async def rate_limit_dependency(
    request: Request,
    rate_string: str = settings.RATE_LIMIT_DEFAULT
):
    """FastAPI dependency for rate limiting."""
    redis_client: AsyncRedis = request.app.state.redis
    limiter = RateLimiter(redis_client)

    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    key = f"rate_limit:{endpoint}:{client_ip}"

    limit, window_seconds = parse_rate_limit(rate_string)

    allowed, info = await limiter.check_rate_limit(key, limit, window_seconds)

    request.state.rate_limit_info = info

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"]),
                "Retry-After": str(window_seconds),
            }
        )
