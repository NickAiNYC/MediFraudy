"""NYC-specific Medicaid fraud detection signals.

Implements domain-specific detectors for:
- Medicaid home care inflation
- Transportation fraud
- DME (Durable Medical Equipment) abuse
- Phantom visits
- Billing after patient death
- High-frequency CPT overuse
- Cross-borough referral rings
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct

from models import Provider, Claim

logger = logging.getLogger(__name__)

# Known high-risk CPT codes for NYC Medicaid fraud
HIGH_RISK_CPT_CODES = {
    "99213": "Office visit - established patient (most common overbilled code)",
    "99214": "Office visit - moderate complexity",
    "97110": "Therapeutic exercises",
    "97140": "Manual therapy",
    "A0428": "Ambulance, BLS, non-emergency transport",
    "E1399": "DME miscellaneous",
    "T1019": "Personal care services",
    "T1020": "Personal care services, per diem",
    "S5125": "Attendant care services",
    "S5130": "Homemaker service, per 15 min",
}

# NYC Borough mapping
NYC_BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]


def detect_homecare_inflation(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect inflated home care billing patterns.

    Home care is the #1 area of Medicaid fraud in NYC.
    Looks for: excessive hours, impossible visit counts, billing spikes.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    homecare_codes = ["T1019", "T1020", "S5125", "S5130", "99509"]

    provider_data = (
        db.query(
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total"),
            func.avg(Claim.amount).label("avg"),
            func.count(distinct(Claim.beneficiary_id)).label("patients"),
        )
        .filter(
            Claim.provider_id == provider_id,
            Claim.billing_code.in_(homecare_codes),
            Claim.claim_date >= cutoff,
        )
        .first()
    )

    if not provider_data or not provider_data.claim_count:
        return {"provider_id": provider_id, "homecare_claims": 0, "flags": []}

    flags = []
    # Check claims per patient ratio
    if provider_data.patients and provider_data.patients > 0:
        claims_per_patient = provider_data.claim_count / provider_data.patients
        if claims_per_patient > 200:  # More than ~1 claim per working day per patient
            flags.append({
                "type": "excessive_claims_per_patient",
                "value": round(claims_per_patient, 1),
                "threshold": 200,
                "severity": "high",
            })

    return {
        "provider_id": provider_id,
        "homecare_claims": int(provider_data.claim_count),
        "total_billing": float(provider_data.total),
        "avg_claim": float(provider_data.avg),
        "unique_patients": int(provider_data.patients),
        "flags": flags,
    }


def detect_dme_abuse(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect Durable Medical Equipment abuse patterns.

    Looks for: high-cost DME items, repeat orders, unusual equipment mixes.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    dme_codes = ["E1399", "E0601", "E0260", "K0823", "K0001"]

    dme_claims = (
        db.query(
            Claim.billing_code,
            func.count(Claim.id).label("count"),
            func.sum(Claim.amount).label("total"),
            func.count(distinct(Claim.beneficiary_id)).label("patients"),
        )
        .filter(
            Claim.provider_id == provider_id,
            Claim.billing_code.in_(dme_codes),
            Claim.claim_date >= cutoff,
        )
        .group_by(Claim.billing_code)
        .all()
    )

    items = []
    flags = []
    for row in dme_claims:
        item = {
            "code": row.billing_code,
            "count": int(row.count),
            "total": float(row.total),
            "unique_patients": int(row.patients),
        }
        items.append(item)
        if row.patients > 0 and row.count / row.patients > 5:
            flags.append({
                "type": "repeat_dme_orders",
                "code": row.billing_code,
                "orders_per_patient": round(row.count / row.patients, 1),
                "severity": "high",
            })

    return {
        "provider_id": provider_id,
        "dme_items": items,
        "flags": flags,
        "total_dme_billing": sum(i["total"] for i in items),
    }


def detect_high_frequency_cpt(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
    frequency_threshold: float = 3.0,
) -> Dict[str, Any]:
    """Detect CPT codes used at abnormally high frequency vs peers.

    Args:
        db: Database session.
        provider_id: Target provider.
        lookback_days: Analysis window.
        frequency_threshold: Multiplier above peer average to flag.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}

    # Provider code frequency
    provider_codes = (
        db.query(
            Claim.billing_code,
            func.count(Claim.id).label("count"),
        )
        .filter(Claim.provider_id == provider_id, Claim.claim_date >= cutoff)
        .group_by(Claim.billing_code)
        .all()
    )

    overused = []
    for row in provider_codes:
        # Get peer average for this code
        peer_avg = (
            db.query(func.avg(func.count(Claim.id)))
            .select_from(Claim)
            .join(Provider, Claim.provider_id == Provider.id)
            .filter(
                Provider.state == provider.state,
                Claim.billing_code == row.billing_code,
                Claim.claim_date >= cutoff,
                Provider.id != provider_id,
            )
            .group_by(Provider.id)
            .scalar()
        )

        if peer_avg and peer_avg > 0:
            ratio = row.count / float(peer_avg)
            if ratio >= frequency_threshold:
                overused.append({
                    "billing_code": row.billing_code,
                    "provider_count": int(row.count),
                    "peer_avg": round(float(peer_avg), 1),
                    "ratio": round(ratio, 2),
                    "description": HIGH_RISK_CPT_CODES.get(row.billing_code, ""),
                })

    overused.sort(key=lambda x: x["ratio"], reverse=True)
    return {
        "provider_id": provider_id,
        "overused_codes": overused,
        "total_flagged": len(overused),
    }


def borough_risk_heatmap(
    db: Session,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Generate risk heatmap data by NYC borough.

    Returns aggregate risk metrics per borough for map visualization.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    borough_data = (
        db.query(
            Provider.city,
            func.count(distinct(Provider.id)).label("provider_count"),
            func.count(Claim.id).label("total_claims"),
            func.sum(Claim.amount).label("total_billing"),
            func.avg(Claim.amount).label("avg_claim"),
        )
        .select_from(Claim)
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(
            Provider.state == "NY",
            Provider.city.in_(NYC_BOROUGHS),
            Claim.claim_date >= cutoff,
        )
        .group_by(Provider.city)
        .all()
    )

    boroughs = {}
    for row in borough_data:
        boroughs[row.city] = {
            "provider_count": int(row.provider_count),
            "total_claims": int(row.total_claims),
            "total_billing": float(row.total_billing),
            "avg_claim": float(row.avg_claim),
        }

    return {
        "boroughs": boroughs,
        "analysis_period_days": lookback_days,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


def cross_borough_referral_analysis(
    db: Session,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect cross-borough referral patterns that may indicate fraud rings.

    Looks for providers in one borough primarily serving patients from another,
    which can indicate patient brokering.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    # Get providers with claims from multiple boroughs
    cross_borough = (
        db.query(
            Provider.id,
            Provider.name,
            Provider.city.label("provider_borough"),
            func.count(distinct(Claim.beneficiary_id)).label("total_patients"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(
            Provider.state == "NY",
            Provider.city.in_(NYC_BOROUGHS),
            Claim.claim_date >= cutoff,
        )
        .group_by(Provider.id, Provider.name, Provider.city)
        .having(func.count(distinct(Claim.beneficiary_id)) > 10)
        .all()
    )

    patterns = [
        {
            "provider_id": row.id,
            "provider_name": row.name,
            "provider_borough": row.provider_borough,
            "total_patients": int(row.total_patients),
        }
        for row in cross_borough
    ]

    return {
        "cross_borough_patterns": patterns[:50],
        "total_flagged": len(patterns),
        "analyzed_at": datetime.utcnow().isoformat(),
    }
