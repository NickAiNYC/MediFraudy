"""Home care fraud detection routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db
from models import Provider, Claim, EVVLog

router = APIRouter()


@router.get("/homecare/sweep", tags=["Home Care"])
def homecare_sweep(
    min_risk_score: int = Query(40, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Provider.id,
            Provider.name,
            Provider.city,
            Provider.npi,
            Provider.licensed_capacity,
            func.count(Claim.id).label("claim_count"),
            func.count(func.distinct(Claim.beneficiary_id)).label("patient_count"),
            func.sum(Claim.amount).label("total_billed"),
            func.avg(Claim.amount).label("avg_claim"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(
            Provider.facility_type.ilike("%home%")
            | Provider.specialty.ilike("%home%")
            | Provider.facility_type.ilike("%cdpap%")
        )
        .group_by(
            Provider.id, Provider.name, Provider.city,
            Provider.npi, Provider.licensed_capacity
        )
        .order_by(func.sum(Claim.amount).desc())
        .limit(limit * 2)
        .all()
    )

    results = []
    for r in rows:
        risk_score = 0
        flags = []

        if r.licensed_capacity and r.patient_count > r.licensed_capacity:
            risk_score += 40
            flags.append("exceeds_licensed_capacity")
        if r.avg_claim and r.avg_claim > 500:
            risk_score += 20
            flags.append("high_avg_claim")
        if r.claim_count > 1000:
            risk_score += 20
            flags.append("high_claim_volume")

        try:
            evv_count = (
                db.query(func.count(EVVLog.id))
                .filter(EVVLog.provider_id == r.id)
                .scalar() or 0
            )
        except Exception:
            evv_count = 0
        if evv_count == 0 and r.claim_count > 10:
            risk_score += 20
            flags.append("no_evv_records")

        if risk_score >= min_risk_score:
            results.append({
                "provider_id": r.id,
                "name": r.name,
                "city": r.city,
                "npi": r.npi,
                "claim_count": r.claim_count,
                "patient_count": r.patient_count,
                "total_billed": round(r.total_billed or 0, 2),
                "avg_claim": round(r.avg_claim or 0, 2),
                "licensed_capacity": r.licensed_capacity,
                "evv_records": evv_count,
                "risk_score": min(risk_score, 100),
                "flags": flags,
            })
        if len(results) >= limit:
            break

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"providers": results, "count": len(results), "min_risk_score": min_risk_score}


@router.get("/homecare/trending-patterns", tags=["Home Care"])
def homecare_trending_patterns(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT 
            c.billing_code,
            DATE_TRUNC('month', c.claim_date) AS month,
            COUNT(c.id) AS claim_count,
            SUM(c.amount) AS total_billed,
            COUNT(DISTINCT c.beneficiary_id) AS unique_patients,
            COUNT(DISTINCT c.provider_id) AS unique_providers
        FROM claims c
        JOIN providers p ON c.provider_id = p.id
        WHERE 
            (p.facility_type ILIKE '%home%' OR p.specialty ILIKE '%home%')
            AND c.claim_date >= NOW() - INTERVAL '12 months'
        GROUP BY c.billing_code, DATE_TRUNC('month', c.claim_date)
        ORDER BY total_billed DESC
        LIMIT 200
    """)).fetchall()

    return {
        "trending_patterns": [
            {
                "billing_code": r[0],
                "month": str(r[1])[:7] if r[1] else None,
                "claim_count": r[2],
                "total_billed": round(float(r[3] or 0), 2),
                "unique_patients": r[4],
                "unique_providers": r[5],
            }
            for r in rows
        ],
        "count": len(rows),
    }
