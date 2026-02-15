"""Pydantic schemas for risk scoring and evidence APIs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RiskScoreResponse(BaseModel):
    """Response model for provider risk score."""
    provider_id: int
    provider_name: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: str  # LOW, REVIEW, HIGH
    drivers: List[str]
    sub_scores: Dict[str, float]
    analyzed_at: str
    lookback_days: int


class BatchRiskRequest(BaseModel):
    """Request model for batch risk scoring."""
    provider_ids: Optional[List[int]] = None
    min_score: int = Field(0, ge=0, le=100)
    limit: int = Field(100, ge=1, le=500)


class EvidencePackageResponse(BaseModel):
    """Response model for evidence package."""
    provider: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    statistical_comparison: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    claim_breakdown: List[Dict[str, Any]]
    network_summary: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    litigation_narrative: str
    generated_at: str
    lookback_days: int
    disclaimer: str


class AnomalySpikesResponse(BaseModel):
    """Response model for billing spike detection."""
    provider_id: int
    spikes: List[Dict[str, Any]]
    total_codes_analyzed: int
    analyzed_at: Optional[str] = None


class LoginRequest(BaseModel):
    """Authentication request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Authentication response."""
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int


class AuditLogEntry(BaseModel):
    """Audit log record."""
    user: str
    action: str
    resource: str
    resource_id: Optional[str] = None
    timestamp: str
    details: Optional[Dict[str, Any]] = None
