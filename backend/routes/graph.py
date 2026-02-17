"""Graph intelligence routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Provider, Claim, KickbackIndicator, Case, Anomaly

router = APIRouter()


@router.get("/graph/network-stats", tags=["Graph"])
def get_network_stats(db: Session = Depends(get_db)):
    return {
        "nodes": {
            "providers": db.query(Provider).count(),
            "high_risk_providers": db.query(KickbackIndicator)
                .filter(KickbackIndicator.risk_score >= 50).count(),
        },
        "edges": {
            "claims": db.query(Claim).count(),
            "anomalies": db.query(Anomaly).count(),
        },
        "cases": db.query(Case).count(),
        "total_billed": round(float(db.query(func.sum(Claim.amount)).scalar() or 0), 2),
        "currency": "USD",
    }


@router.get("/graph/fraud-rings", tags=["Graph"])
def get_fraud_rings(
    min_score: int = Query(50, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    indicators = (
        db.query(KickbackIndicator)
        .filter(KickbackIndicator.risk_score >= min_score)
        .order_by(KickbackIndicator.risk_score.desc())
        .limit(limit)
        .all()
    )

    rings = []
    for ki in indicators:
        provider = db.query(Provider).filter(Provider.id == ki.provider_id).first()
        if not provider:
            continue
        top_beneficiaries = (
            db.query(
                Claim.beneficiary_id,
                func.count(func.distinct(Claim.provider_id)).label("shared_providers"),
                func.sum(Claim.amount).label("total"),
            )
            .filter(Claim.provider_id == ki.provider_id)
            .group_by(Claim.beneficiary_id)
            .order_by(func.sum(Claim.amount).desc())
            .limit(5)
            .all()
        )
        rings.append({
            "ring_id": f"ring_{ki.provider_id}",
            "anchor_provider": {
                "id": provider.id,
                "name": provider.name,
                "npi": provider.npi,
                "city": provider.city,
                "facility_type": provider.facility_type,
            },
            "risk_score": ki.risk_score,
            "confidence": ki.confidence,
            "referral_network": ki.referral_network or {},
            "top_shared_beneficiaries": [
                {
                    "beneficiary_id": b.beneficiary_id,
                    "shared_with_providers": b.shared_providers,
                    "total_billed": round(b.total or 0, 2),
                }
                for b in top_beneficiaries
            ],
            "enrollment_spike_dates": ki.enrollment_spike_dates or [],
        })

    return {"fraud_rings": rings, "count": len(rings), "min_score": min_score}
