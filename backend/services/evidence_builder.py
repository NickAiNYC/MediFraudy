"""Evidence package builder for litigation-ready case exports.

Generates comprehensive case packages including:
- Timeline of suspicious activity
- Statistical comparisons
- Network graph summary
- Risk score explanation
- Litigation narrative
- Supporting claim data
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Provider, Claim, Anomaly, Case, TimelineEvent
from services.risk_scoring import calculate_risk_score

logger = logging.getLogger(__name__)


def generate_case_package(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Generate a complete litigation-ready evidence package.

    This is the primary weapon for qui tam / whistleblower law firms.

    Args:
        db: Database session.
        provider_id: Target provider.
        lookback_days: Analysis window.

    Returns:
        Complete evidence package as structured dictionary.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}

    # Risk assessment
    risk_result = calculate_risk_score(db, provider_id, lookback_days)

    # Statistical comparisons
    stats = _build_statistical_comparison(db, provider, lookback_days)

    # Timeline of suspicious activity
    timeline = _build_suspicious_timeline(db, provider_id, lookback_days)

    # Claim breakdown
    claim_breakdown = _build_claim_breakdown(db, provider_id, lookback_days)

    # Network summary
    try:
        from services.network_analysis import get_network_summary
        network = get_network_summary(db, provider_id)
    except Exception as e:
        logger.warning(f"Network analysis unavailable: {e}")
        network = {"connected_entities": 0, "in_fraud_ring": False}

    # Anomaly summary
    anomalies = _get_anomaly_summary(db, provider_id)

    # Auto-generate litigation narrative
    narrative = _generate_litigation_narrative(
        provider, risk_result, stats, network, anomalies, timeline
    )

    return {
        "provider": {
            "id": provider.id,
            "npi": provider.npi,
            "name": provider.name,
            "address": provider.address,
            "city": provider.city,
            "state": provider.state,
            "facility_type": provider.facility_type,
            "licensed_capacity": provider.licensed_capacity,
        },
        "risk_assessment": risk_result,
        "statistical_comparison": stats,
        "timeline": timeline,
        "claim_breakdown": claim_breakdown,
        "network_summary": network,
        "anomalies": anomalies,
        "litigation_narrative": narrative,
        "generated_at": datetime.utcnow().isoformat(),
        "lookback_days": lookback_days,
        "disclaimer": (
            "This document contains confidential information prepared for potential "
            "False Claims Act litigation. Protected by attorney-client privilege."
        ),
    }


def _build_statistical_comparison(
    db: Session, provider: Provider, lookback_days: int
) -> Dict[str, Any]:
    """Build statistical comparisons vs peers."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    # Provider stats
    provider_stats = (
        db.query(
            func.count(Claim.id).label("total_claims"),
            func.sum(Claim.amount).label("total_amount"),
            func.avg(Claim.amount).label("avg_amount"),
            func.count(func.distinct(Claim.beneficiary_id)).label("unique_beneficiaries"),
            func.count(func.distinct(Claim.billing_code)).label("unique_codes"),
        )
        .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
        .first()
    )

    # Borough/city peer stats
    peer_stats = (
        db.query(
            func.avg(Claim.amount).label("peer_avg"),
            func.count(Claim.id).label("peer_total"),
        )
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(
            Provider.city == provider.city,
            Provider.state == provider.state,
            Provider.id != provider.id,
            Claim.claim_date >= cutoff,
        )
        .first()
    )

    result = {
        "provider_claims": int(provider_stats.total_claims or 0),
        "provider_total_billing": float(provider_stats.total_amount or 0),
        "provider_avg_claim": float(provider_stats.avg_amount or 0),
        "unique_beneficiaries": int(provider_stats.unique_beneficiaries or 0),
        "unique_billing_codes": int(provider_stats.unique_codes or 0),
    }

    if peer_stats and peer_stats.peer_avg:
        result["peer_avg_claim"] = float(peer_stats.peer_avg)
        result["peer_deviation_ratio"] = round(
            float(provider_stats.avg_amount or 0) / float(peer_stats.peer_avg), 2
        ) if peer_stats.peer_avg else None
        result["borough"] = provider.city
    else:
        result["peer_avg_claim"] = None
        result["peer_deviation_ratio"] = None

    return result


def _build_suspicious_timeline(
    db: Session, provider_id: int, lookback_days: int
) -> List[Dict[str, Any]]:
    """Build a timeline of suspicious billing patterns."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    monthly = (
        db.query(
            func.date_trunc("month", Claim.claim_date).label("month"),
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
            func.count(func.distinct(Claim.beneficiary_id)).label("unique_patients"),
        )
        .filter(Claim.provider_id == provider_id, Claim.claim_date >= cutoff)
        .group_by("month")
        .order_by("month")
        .all()
    )

    timeline = []
    prev_count = None
    for row in monthly:
        entry = {
            "month": str(row.month.date()) if row.month else None,
            "claim_count": int(row.claim_count),
            "total_amount": float(row.total_amount),
            "unique_patients": int(row.unique_patients),
        }
        if prev_count and prev_count > 0:
            change = (row.claim_count - prev_count) / prev_count
            entry["change_pct"] = round(change * 100, 1)
            if change > 0.5:
                entry["flag"] = "spike"
            elif change < -0.5:
                entry["flag"] = "drop"
        prev_count = row.claim_count
        timeline.append(entry)

    return timeline


def _build_claim_breakdown(
    db: Session, provider_id: int, lookback_days: int
) -> List[Dict[str, Any]]:
    """Break down claims by billing code."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    breakdown = (
        db.query(
            Claim.billing_code,
            func.count(Claim.id).label("count"),
            func.sum(Claim.amount).label("total"),
            func.avg(Claim.amount).label("avg"),
        )
        .filter(Claim.provider_id == provider_id, Claim.claim_date >= cutoff)
        .group_by(Claim.billing_code)
        .order_by(func.sum(Claim.amount).desc())
        .limit(20)
        .all()
    )

    return [
        {
            "billing_code": row.billing_code,
            "claim_count": int(row.count),
            "total_amount": float(row.total),
            "avg_amount": float(row.avg),
        }
        for row in breakdown
    ]


def _get_anomaly_summary(db: Session, provider_id: int) -> List[Dict[str, Any]]:
    """Get anomaly summary for the provider."""
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.provider_id == provider_id)
        .order_by(Anomaly.z_score.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "billing_code": a.billing_code,
            "z_score": round(a.z_score, 2),
            "type": a.anomaly_type,
            "detected_at": str(a.detected_at) if a.detected_at else None,
        }
        for a in anomalies
    ]


def _generate_litigation_narrative(
    provider: Provider,
    risk_result: Dict,
    stats: Dict,
    network: Dict,
    anomalies: List[Dict],
    timeline: List[Dict],
) -> str:
    """Auto-generate a litigation narrative paragraph.

    This narrative summarizes the key fraud indicators in a format
    suitable for inclusion in a qui tam complaint or disclosure statement.
    """
    parts = []

    # Opening
    parts.append(
        f"Provider {provider.name} (NPI: {provider.npi}), located in "
        f"{provider.city or 'New York'}, {provider.state or 'NY'}, "
        f"has been identified with a composite fraud risk score of "
        f"{risk_result.get('risk_score', 0)} out of 100 "
        f"({risk_result.get('risk_level', 'UNKNOWN')} risk)."
    )

    # Billing deviation
    if stats.get("peer_deviation_ratio") and stats["peer_deviation_ratio"] > 1.5:
        parts.append(
            f"Statistical analysis shows billing at {stats['peer_deviation_ratio']}x "
            f"the {stats.get('borough', 'borough')} peer average, "
            f"with total claims of ${stats.get('provider_total_billing', 0):,.0f} "
            f"across {stats.get('provider_claims', 0)} submissions."
        )

    # Anomalies
    if anomalies:
        top_z = anomalies[0].get("z_score", 0)
        parts.append(
            f"Statistical outlier analysis detected {len(anomalies)} anomalies, "
            f"with the highest z-score of {top_z:.1f}."
        )

    # Spikes
    spike_months = [t for t in timeline if t.get("flag") == "spike"]
    if spike_months:
        parts.append(
            f"Temporal analysis identified {len(spike_months)} billing spike(s) "
            f"within the analysis window."
        )

    # Network
    connected = network.get("connected_entities", 0)
    if connected > 0:
        high_risk = network.get("high_risk_connections", 0)
        parts.append(
            f"Network analysis shows connections to {connected} entities"
            + (f", including {high_risk} high-risk entities" if high_risk > 0 else "")
            + "."
        )
    if network.get("in_fraud_ring"):
        ring = network.get("fraud_ring_info", {})
        parts.append(
            f"The provider has been identified within a suspected fraud ring "
            f"of {ring.get('ring_size', 'multiple')} entities "
            f"(ring fraud score: {ring.get('fraud_score', 'N/A')})."
        )

    # Risk drivers
    drivers = risk_result.get("drivers", [])
    if drivers:
        driver_str = "; ".join(drivers[:5])
        parts.append(f"Key risk drivers include: {driver_str}.")

    return " ".join(parts)
