"""Authentication API routes."""

import logging
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from schemas.risk import LoginRequest, TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Demo users (in production, store in database)
DEMO_USERS = {
    "partner": {
        "password_hash": get_password_hash("partner123"),
        "role": "partner",
        "full_name": "Senior Partner",
    },
    "associate": {
        "password_hash": get_password_hash("associate123"),
        "role": "associate",
        "full_name": "Associate Attorney",
    },
    "investigator": {
        "password_hash": get_password_hash("investigator123"),
        "role": "investigator",
        "full_name": "Fraud Investigator",
    },
    "auditor": {
        "password_hash": get_password_hash("auditor123"),
        "role": "auditor",
        "full_name": "Compliance Auditor",
    },
}


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """Authenticate user and return JWT token.

    Demo credentials:
    - partner / partner123
    - associate / associate123
    - investigator / investigator123
    - auditor / auditor123
    """
    user = DEMO_USERS.get(request.username)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = create_access_token(
        data={"sub": request.username, "role": user["role"]}
    )
    return TokenResponse(
        access_token=token,
        role=user["role"],
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me")
def get_current_user_info(
    user=None,
):
    """Get current authenticated user info.

    Returns user details if authenticated, or anonymous status.
    """
    if user is None:
        return {"authenticated": False, "role": "anonymous"}
    return {
        "authenticated": True,
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
    }
