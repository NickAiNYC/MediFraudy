"""Enterprise middleware for rate limiting and audit logging.

Implements:
- IP-based rate limiting with configurable windows
- Request audit logging for compliance tracking
- Input validation headers
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP-based rate limiting middleware.

    Limits the number of requests per IP address within a rolling time window.
    Returns HTTP 429 when the limit is exceeded.

    Args:
        app: FastAPI application.
        requests_per_minute: Maximum requests per IP per minute.
        enabled: Whether rate limiting is active (disable for dev).
    """

    def __init__(self, app, requests_per_minute: int = 120, enabled: bool = True):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.enabled = enabled
        self._request_counts: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries outside the 60-second window
        self._request_counts[client_ip] = [
            ts for ts in self._request_counts[client_ip]
            if now - ts < 60
        ]

        if len(self._request_counts[client_ip]) >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for {client_ip}: "
                f"{len(self._request_counts[client_ip])}/{self.requests_per_minute} req/min"
            )
            return Response(
                content='{"detail": "Rate limit exceeded. Please retry later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self._request_counts[client_ip].append(now)
        remaining = self.requests_per_minute - len(self._request_counts[client_ip])

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Request-level audit logging for compliance.

    Logs every request with user info, resource accessed, and timestamp.
    Write-operation logs (POST/PUT/DELETE) are stored at INFO level,
    read operations at DEBUG level.

    Args:
        app: FastAPI application.
        enabled: Whether audit logging is active.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip logging for health checks and static assets
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Extract user from JWT if present
        user = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                # Import inside function to avoid circular imports with FastAPI app
                from core.security import decode_token
                token_data = decode_token(auth_header.split(" ", 1)[1])
                user = token_data.sub
            except Exception:
                user = "invalid_token"

        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 1)

        log_data = {
            "user": user,
            "method": method,
            "path": path,
            "status": response.status_code,
            "ip": client_ip,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if method in ("POST", "PUT", "DELETE", "PATCH"):
            logger.info(f"AUDIT: {log_data}")
        else:
            logger.debug(f"AUDIT: {log_data}")

        return response
