"""
Rate limiting using SlowAPI with Redis backend.
Prevents API abuse and DDoS attacks.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, Response
import redis
from typing import Callable
import os

# Redis connection for distributed rate limiting
try:
    redis_client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
        socket_timeout=5
    )
    redis_client.ping()
except:
    redis_client = None


def get_client_identifier(request: Request) -> str:
    """
    Get unique client identifier for rate limiting.
    Uses authenticated user ID if available, otherwise IP address.
    """
    # Check if user is authenticated
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_client_identifier,
    storage_uri=os.getenv("REDIS_URL", "memory://") if redis_client else "memory://",
    default_limits=["100/hour"],
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    Returns 429 with retry-after header.
    """
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded. Try again in {exc.retry_after} seconds.",
            "retry_after": exc.retry_after
        },
        status_code=429,
        headers={"Retry-After": str(int(exc.retry_after))}
    )


# Decorator for custom rate limits
def custom_rate_limit(limit: str):
    """
    Custom rate limit decorator.
    
    Usage:
        @custom_rate_limit("50/hour")
        async def expensive_endpoint():
            ...
    """
    return limiter.limit(limit)


# Specific rate limits for different endpoint types
def sensitive_rate_limit():
    """Rate limit for sensitive operations (10/hour)"""
    return limiter.limit("10/hour")


def standard_rate_limit():
    """Standard rate limit (100/hour)"""
    return limiter.limit("100/hour")


def generous_rate_limit():
    """Generous rate limit for read operations (1000/hour)"""
    return limiter.limit("1000/hour")
