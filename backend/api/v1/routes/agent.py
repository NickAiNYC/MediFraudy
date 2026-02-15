"""DeepSeek AI legal assistant API routes.

Provides chat endpoints for the NYC Medicaid fraud legal assistant,
with optional provider context injection for data-informed analysis.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.deepseek_agent import get_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class ChatRequest(BaseModel):
    """Chat message request."""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default", max_length=100)
    provider_id: Optional[int] = Field(default=None, description="Optional provider ID to include as context")


class ChatResponse(BaseModel):
    """Chat message response."""
    response: str
    session_id: str
    model: str
    configured: bool
    error: Optional[bool] = None
    usage: Optional[dict] = None
    timestamp: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Chat with the NYC Medicaid fraud legal assistant.

    Send a message and optionally include a provider_id to give the
    agent context about a specific provider's risk profile, anomalies,
    and network connections.

    Example questions:
    - "What are the strongest FCA theories for a provider billing 4.8x the borough median?"
    - "How would you structure a qui tam complaint for capacity violations?"
    - "What's the estimated whistleblower reward for a $120M fraud case?"
    - "Analyze this provider's risk profile and suggest next steps."
    """
    agent = get_agent()

    # Build provider context if requested
    provider_context = None
    if request.provider_id:
        provider_context = _build_provider_context(db, request.provider_id)

    result = await agent.chat(
        message=request.message,
        session_id=request.session_id,
        provider_context=provider_context,
    )

    return ChatResponse(**result)


@router.post("/clear-session")
async def clear_session(session_id: str = "default"):
    """Clear conversation history for a session."""
    agent = get_agent()
    agent.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@router.get("/status")
async def agent_status():
    """Check if the DeepSeek agent is configured and ready."""
    agent = get_agent()
    return {
        "configured": agent.is_configured,
        "model": agent.model,
        "description": "NYC Medicaid Fraud Legal Assistant powered by DeepSeek",
    }


def _build_provider_context(db: Session, provider_id: int) -> Optional[dict]:
    """Build provider context for the agent from the database."""
    from models import Provider, Anomaly

    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return None

    context: dict = {
        "provider": {
            "name": provider.name,
            "npi": provider.npi,
            "city": provider.city,
            "state": provider.state,
            "facility_type": provider.facility_type,
            "licensed_capacity": provider.licensed_capacity,
        }
    }

    # Add risk score if available
    try:
        from services.risk_scoring import calculate_risk_score
        risk = calculate_risk_score(db, provider_id)
        context["risk_score"] = risk.get("risk_score", 0)
        context["risk_level"] = risk.get("risk_level", "UNKNOWN")
        context["drivers"] = risk.get("drivers", [])
    except Exception as e:
        logger.warning(f"Could not compute risk score for context: {e}")

    # Add anomalies
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.provider_id == provider_id)
        .order_by(Anomaly.z_score.desc())
        .limit(10)
        .all()
    )
    context["anomalies"] = [
        {"billing_code": a.billing_code, "z_score": a.z_score, "type": a.anomaly_type}
        for a in anomalies
    ]

    # Add litigation narrative if available
    try:
        from services.evidence_builder import generate_case_package
        pkg = generate_case_package(db, provider_id)
        context["narrative"] = pkg.get("litigation_narrative", "")
    except Exception as e:
        logger.warning(f"Could not build narrative for context: {e}")

    return context
