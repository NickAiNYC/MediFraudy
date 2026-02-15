"""Anomaly detection engine combining multiple detection methods.

Layers:
1. Statistical anomaly detection (Z-score, peer group outliers)
2. Temporal clustering (sudden volume changes)
3. Behavioral pattern detection
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Provider, Claim

# Spike severity thresholds (ratio vs baseline)
CRITICAL_SPIKE_RATIO = 5.0
HIGH_SPIKE_RATIO = 3.0

logger = logging.getLogger(__name__)


def detect_billing_spikes(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
    spike_threshold: float = 2.0,
) -> Dict[str, Any]:
    """Detect sudden billing volume spikes per CPT code.

    Args:
        db: Database session.
        provider_id: Target provider.
        lookback_days: Analysis window.
        spike_threshold: Multiplier threshold for spike detection.

    Returns:
        Dictionary with detected spikes and metadata.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    try:
        monthly = (
            db.query(
                Claim.billing_code,
                func.date_trunc("month", Claim.claim_date).label("month"),
                func.count(Claim.id).label("count"),
                func.sum(Claim.amount).label("total"),
            )
            .filter(Claim.provider_id == provider_id, Claim.claim_date >= cutoff)
            .group_by(Claim.billing_code, "month")
            .order_by(Claim.billing_code, "month")
            .all()
        )
    except Exception as e:
        logger.warning(f"Billing spike detection unavailable (requires PostgreSQL): {e}")
        db.rollback()
        return {"provider_id": provider_id, "spikes": [], "total_codes_analyzed": 0, "note": "Requires PostgreSQL"}

    if not monthly:
        return {"provider_id": provider_id, "spikes": [], "total_codes_analyzed": 0}

    # Group by billing code
    code_data: Dict[str, List[float]] = {}
    for row in monthly:
        code_data.setdefault(row.billing_code, []).append(float(row.count))

    spikes = []
    for code, counts in code_data.items():
        if len(counts) < 3:
            continue
        baseline = np.mean(counts[:-1])
        if baseline == 0:
            continue
        latest = counts[-1]
        ratio = latest / baseline
        if ratio >= spike_threshold:
            spikes.append({
                "billing_code": code,
                "baseline_avg": round(baseline, 1),
                "latest_count": latest,
                "spike_ratio": round(ratio, 2),
                "severity": "critical" if ratio > CRITICAL_SPIKE_RATIO else "high" if ratio > HIGH_SPIKE_RATIO else "moderate",
            })

    spikes.sort(key=lambda x: x["spike_ratio"], reverse=True)
    return {
        "provider_id": provider_id,
        "spikes": spikes,
        "total_codes_analyzed": len(code_data),
        "analyzed_at": datetime.utcnow().isoformat(),
    }


def detect_impossible_service_density(
    db: Session,
    provider_id: int,
    max_daily_services: int = 50,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect days where service count is physically impossible.

    Args:
        db: Database session.
        provider_id: Target provider.
        max_daily_services: Maximum plausible daily services.
        lookback_days: Analysis window.

    Returns:
        Dictionary with impossible service days.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    daily = (
        db.query(
            Claim.claim_date,
            func.count(Claim.id).label("service_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .filter(Claim.provider_id == provider_id, Claim.claim_date >= cutoff)
        .group_by(Claim.claim_date)
        .having(func.count(Claim.id) > max_daily_services)
        .order_by(func.count(Claim.id).desc())
        .all()
    )

    impossible_days = [
        {
            "date": str(row.claim_date),
            "service_count": int(row.service_count),
            "total_amount": float(row.total_amount),
            "excess_factor": round(int(row.service_count) / max_daily_services, 1),
        }
        for row in daily
    ]

    return {
        "provider_id": provider_id,
        "impossible_days": impossible_days,
        "count": len(impossible_days),
        "max_daily_threshold": max_daily_services,
    }


def detect_duplicate_claims(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect potential duplicate claims (same beneficiary, code, date).

    Args:
        db: Database session.
        provider_id: Target provider.
        lookback_days: Analysis window.

    Returns:
        Dictionary with potential duplicates.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    dupes = (
        db.query(
            Claim.beneficiary_id,
            Claim.billing_code,
            Claim.claim_date,
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .filter(
            Claim.provider_id == provider_id,
            Claim.claim_date >= cutoff,
            Claim.beneficiary_id.isnot(None),
        )
        .group_by(Claim.beneficiary_id, Claim.billing_code, Claim.claim_date)
        .having(func.count(Claim.id) > 1)
        .order_by(func.count(Claim.id).desc())
        .limit(100)
        .all()
    )

    duplicates = [
        {
            "beneficiary_id": row.beneficiary_id,
            "billing_code": row.billing_code,
            "claim_date": str(row.claim_date),
            "duplicate_count": int(row.claim_count),
            "total_amount": float(row.total_amount),
        }
        for row in dupes
    ]

    total_waste = sum(d["total_amount"] * (d["duplicate_count"] - 1) / d["duplicate_count"] for d in duplicates)
    return {
        "provider_id": provider_id,
        "duplicates": duplicates,
        "count": len(duplicates),
        "estimated_waste": round(total_waste, 2),
    }


def detect_billing_after_death(
    db: Session,
    provider_id: int,
) -> Dict[str, Any]:
    """Detect claims submitted for deceased beneficiaries.

    Args:
        db: Database session.
        provider_id: Target provider.

    Returns:
        Dictionary with post-death billing instances.
    """
    from models import Beneficiary

    results = (
        db.query(
            Claim.beneficiary_id,
            Claim.claim_date,
            Claim.billing_code,
            Claim.amount,
            Beneficiary.status_date,
        )
        .join(Beneficiary, Claim.beneficiary_id == Beneficiary.id)
        .filter(
            Claim.provider_id == provider_id,
            Beneficiary.status == "deceased",
            Claim.claim_date > Beneficiary.status_date,
        )
        .order_by(Claim.claim_date.desc())
        .limit(100)
        .all()
    )

    violations = [
        {
            "beneficiary_id": r.beneficiary_id,
            "claim_date": str(r.claim_date),
            "death_date": str(r.status_date),
            "days_after_death": (r.claim_date - r.status_date).days,
            "billing_code": r.billing_code,
            "amount": float(r.amount),
        }
        for r in results
    ]

    return {
        "provider_id": provider_id,
        "post_death_claims": violations,
        "count": len(violations),
        "total_amount": sum(v["amount"] for v in violations),
    }
