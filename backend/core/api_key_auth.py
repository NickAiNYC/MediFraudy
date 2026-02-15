"""API key authentication and tiered rate limiting.

Implements:
- API key validation via X-API-Key header
- Tiered rate limits: Free (100/day), Pro (10k/day), Enterprise (unlimited)
- Daily request counter reset
- Key generation utility
"""

import logging
import secrets
from datetime import date, datetime
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from database import get_db

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limits per tier (requests per day)
TIER_LIMITS = {
    "free": 100,
    "pro": 10_000,
    "enterprise": None,  # Unlimited
}


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return secrets.token_hex(32)


def _get_api_key_record(db: Session, key: str):
    """Look up an API key record from the database."""
    from models import APIKey
    return db.query(APIKey).filter(APIKey.key == key, APIKey.is_active.is_(True)).first()


def validate_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db),
):
    """Validate API key and enforce tier-based rate limits.

    Returns the API key record if valid, or None if no key is provided
    (allowing unauthenticated access with the most restrictive limits).
    """
    if api_key is None:
        return None

    record = _get_api_key_record(db, api_key)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    # Check expiration
    if record.expires_at and record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Reset daily counter if it's a new day
    today = date.today()
    if record.last_request_date != today:
        record.requests_today = 0
        record.last_request_date = today

    # Check rate limit
    limit = TIER_LIMITS.get(record.tier)
    if limit is not None and record.requests_today >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily rate limit exceeded for {record.tier} tier ({limit} requests/day)",
            headers={"Retry-After": "86400"},
        )

    # Increment counter
    record.requests_today += 1
    db.commit()

    return record
