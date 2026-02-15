"""API key management routes.

Provides endpoints to create, list, and revoke API keys.
Requires JWT authentication with partner role.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.api_key_auth import generate_api_key, TIER_LIMITS
from core.security import require_role
from database import get_db
from models import APIKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


class APIKeyCreateRequest(BaseModel):
    name: str
    tier: str = "free"
    owner_email: str


class APIKeyResponse(BaseModel):
    id: int
    name: str
    tier: str
    owner_email: str
    is_active: bool
    requests_today: int
    daily_limit: Optional[int]
    created_at: Optional[str]
    key: Optional[str] = None  # Only returned on creation


@router.post("", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: APIKeyCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("partner")),
):
    """Create a new API key. Requires partner role."""
    if request.tier not in TIER_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {list(TIER_LIMITS.keys())}",
        )

    key = generate_api_key()
    api_key = APIKey(
        key=key,
        name=request.name,
        tier=request.tier,
        owner_email=request.owner_email,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        tier=api_key.tier,
        owner_email=api_key.owner_email,
        is_active=api_key.is_active,
        requests_today=api_key.requests_today,
        daily_limit=TIER_LIMITS.get(api_key.tier),
        created_at=str(api_key.created_at) if api_key.created_at else None,
        key=key,  # Only returned on creation
    )


@router.get("")
def list_api_keys(
    db: Session = Depends(get_db),
    user=Depends(require_role("partner")),
):
    """List all API keys. Requires partner role."""
    keys = db.query(APIKey).all()
    return {
        "api_keys": [
            APIKeyResponse(
                id=k.id,
                name=k.name,
                tier=k.tier,
                owner_email=k.owner_email,
                is_active=k.is_active,
                requests_today=k.requests_today,
                daily_limit=TIER_LIMITS.get(k.tier),
                created_at=str(k.created_at) if k.created_at else None,
            ).model_dump()
            for k in keys
        ],
        "count": len(keys),
    }


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("partner")),
):
    """Revoke an API key. Requires partner role."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()
    return {"detail": "API key revoked", "id": key_id}
