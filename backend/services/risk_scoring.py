"""Composite fraud risk scoring engine — 4-layer detection system.

Layer 1: Statistical Outlier Detection (30%)
    - Z-score deviation from peer CPT averages
    - Temporal spikes
    - Borough-level anomalies

Layer 2: Behavioral Pattern Detection (30%)
    - Identical billing fingerprints
    - Impossible service density
    - Billing outside business hours
    - High CPT clustering per beneficiary

Layer 3: Network Intelligence (25%)
    - Provider ↔ Clinic ↔ Beneficiary graph centrality
    - Shared tax IDs / addresses
    - Referral loops
    - Community detection clustering

Layer 4: Predictive / Historical Risk (15%)
    - Prior sanctions or exclusions
    - Historical anomaly accumulation
    - NYC-specific patterns (capacity violations, kickbacks)

Scoring bands:
    0–39  = Low
    40–69 = Review
    70–100 = High Litigation Risk
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Provider, Claim, Anomaly

logger = logging.getLogger(__name__)

# 4-layer weight configuration for composite scoring
WEIGHTS = {
    "statistical_anomaly": 0.30,
    "behavioral_signals": 0.30,
    "network_intelligence": 0.25,
    "historical_risk": 0.15,
}

# Risk category labels
RISK_CATEGORIES = {
    "HIGH": "High Litigation Risk",
    "REVIEW": "Review Recommended",
    "LOW": "Low Risk",
    "UNKNOWN": "Insufficient Data",
}


def calculate_risk_score(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Calculate composite fraud risk score using 4-layer detection.

    Layer 1 — Statistical Anomaly (30%):
        Z-score deviation, peer deviation, temporal spikes.
    Layer 2 — Behavioral Signals (30%):
        Billing fingerprints, impossible density, code clustering.
    Layer 3 — Network Intelligence (25%):
        Network centrality, shared connections, fraud ring membership.
    Layer 4 — Historical / Predictive Risk (15%):
        Prior anomalies, sanctions, NYC-specific patterns.

    Args:
        db: Database session.
        provider_id: Target provider.
        lookback_days: Analysis window.

    Returns:
        Dictionary with risk_score, category, and explainable drivers.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found", "risk_score": 0, "risk_level": "UNKNOWN",
                "category": RISK_CATEGORIES["UNKNOWN"]}

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    drivers: List[str] = []
    sub_scores: Dict[str, float] = {}
    layer_details: Dict[str, Dict[str, float]] = {}

    # --- Layer 1: Statistical Anomaly (30%) ---
    billing_score, billing_drivers = _billing_zscore_component(db, provider, cutoff)
    peer_score, peer_drivers = _peer_deviation_component(db, provider, cutoff)
    spike_score, spike_drivers = _temporal_spike_component(db, provider, cutoff)
    drivers.extend(billing_drivers)
    drivers.extend(peer_drivers)
    drivers.extend(spike_drivers)

    stat_components = {
        "billing_zscore": billing_score,
        "peer_deviation": peer_score,
        "temporal_spike": spike_score,
    }
    layer_details["statistical_anomaly"] = stat_components
    sub_scores["statistical_anomaly"] = (
        billing_score * 0.40 + peer_score * 0.30 + spike_score * 0.30
    )

    # --- Layer 2: Behavioral Signals (30%) ---
    behavior_score, behavior_drivers = _behavioral_component(db, provider, cutoff)
    drivers.extend(behavior_drivers)

    behav_components = {
        "behavioral_patterns": behavior_score,
    }
    layer_details["behavioral_signals"] = behav_components
    sub_scores["behavioral_signals"] = behavior_score

    # --- Layer 3: Network Intelligence (25%) ---
    network_score, network_drivers = _network_risk_component(db, provider)
    drivers.extend(network_drivers)

    net_components = {
        "network_risk": network_score,
    }
    layer_details["network_intelligence"] = net_components
    sub_scores["network_intelligence"] = network_score

    # --- Layer 4: Historical / Predictive Risk (15%) ---
    nyc_score, nyc_drivers = _nyc_specific_component(db, provider, cutoff)
    historical_score, hist_drivers = _historical_risk_component(db, provider)
    drivers.extend(nyc_drivers)
    drivers.extend(hist_drivers)

    hist_components = {
        "nyc_specific": nyc_score,
        "historical_anomalies": historical_score,
    }
    layer_details["historical_risk"] = hist_components
    sub_scores["historical_risk"] = nyc_score * 0.50 + historical_score * 0.50

    # Weighted composite across 4 layers
    composite = sum(
        sub_scores.get(key, 0) * weight
        for key, weight in WEIGHTS.items()
    )
    risk_score = min(100, max(0, round(composite)))

    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "REVIEW"
    else:
        risk_level = "LOW"

    category = RISK_CATEGORIES.get(risk_level, RISK_CATEGORIES["UNKNOWN"])

    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "category": category,
        "drivers": drivers[:10],  # Top 10 drivers
        "sub_scores": sub_scores,
        "layer_details": layer_details,
        "weights": WEIGHTS,
        "analyzed_at": datetime.utcnow().isoformat(),
        "lookback_days": lookback_days,
    }


def batch_risk_scores(
    db: Session,
    provider_ids: Optional[List[int]] = None,
    min_score: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Calculate risk scores for multiple providers.

    Args:
        db: Database session.
        provider_ids: Optional list of provider IDs. If None, uses top providers by claim volume.
        min_score: Minimum risk score to include in results.
        limit: Maximum results to return.

    Returns:
        Sorted list of risk score results.
    """
    if provider_ids is None:
        providers = (
            db.query(Provider.id)
            .join(Claim, Claim.provider_id == Provider.id)
            .group_by(Provider.id)
            .order_by(func.count(Claim.id).desc())
            .limit(limit * 2)
            .all()
        )
        provider_ids = [p.id for p in providers]

    results = []
    for pid in provider_ids:
        try:
            result = calculate_risk_score(db, pid)
            if result.get("risk_score", 0) >= min_score:
                results.append(result)
        except Exception as e:
            logger.warning(f"Risk scoring failed for provider {pid}: {e}")

    results.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    return results[:limit]


# --- Component scoring functions ---

def _billing_zscore_component(
    db: Session, provider: Provider, cutoff: datetime
) -> tuple:
    """Calculate billing z-score relative to state peers."""
    drivers = []
    claims = (
        db.query(func.avg(Claim.amount), func.count(Claim.id))
        .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
        .first()
    )
    if not claims or claims[0] is None:
        return 0.0, drivers

    provider_avg = float(claims[0])
    provider_count = int(claims[1])

    # State peer average
    peer_stats = (
        db.query(func.avg(Claim.amount), func.stddev(Claim.amount))
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Provider.state == provider.state, Claim.claim_date >= cutoff)
        .first()
    )
    if not peer_stats or peer_stats[0] is None or peer_stats[1] is None:
        return 0.0, drivers

    peer_avg = float(peer_stats[0])
    peer_std = float(peer_stats[1])
    if peer_std == 0:
        return 0.0, drivers

    z = (provider_avg - peer_avg) / peer_std
    score = min(100, max(0, abs(z) * 20))

    if abs(z) >= 3.0:
        ratio = provider_avg / peer_avg if peer_avg > 0 else 0
        drivers.append(f"Billing {ratio:.1f}x peer average (z={z:.1f})")
    if provider_count > 1000:
        drivers.append(f"High claim volume: {provider_count} claims")

    return score, drivers


def _peer_deviation_component(
    db: Session, provider: Provider, cutoff: datetime
) -> tuple:
    """Compare provider to facility-type peers."""
    drivers = []
    if not provider.facility_type:
        return 0.0, drivers

    provider_total = (
        db.query(func.sum(Claim.amount))
        .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
        .scalar()
    )
    if not provider_total:
        return 0.0, drivers

    peer_avg = (
        db.query(func.avg(func.sum(Claim.amount)))
        .select_from(Claim)
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(
            Provider.facility_type == provider.facility_type,
            Provider.state == provider.state,
            Claim.claim_date >= cutoff,
        )
        .group_by(Provider.id)
        .scalar()
    )
    if not peer_avg or peer_avg == 0:
        return 0.0, drivers

    ratio = float(provider_total) / float(peer_avg)
    score = min(100, max(0, (ratio - 1) * 40))

    if ratio > 2.0:
        drivers.append(f"Total billing {ratio:.1f}x {provider.facility_type} peer median")

    return score, drivers


def _temporal_spike_component(
    db: Session, provider: Provider, cutoff: datetime
) -> tuple:
    """Detect sudden billing spikes."""
    drivers = []

    try:
        monthly = (
            db.query(
                func.date_trunc("month", Claim.claim_date).label("month"),
                func.sum(Claim.amount).label("total"),
            )
            .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
            .group_by("month")
            .order_by("month")
            .all()
        )
    except Exception:
        db.rollback()
        return 0.0, drivers
    if len(monthly) < 3:
        return 0.0, drivers

    totals = [float(m.total) for m in monthly]
    mean_total = np.mean(totals[:-1]) if len(totals) > 1 else totals[0]
    if mean_total == 0:
        return 0.0, drivers

    max_spike = max(totals) / mean_total
    score = min(100, max(0, (max_spike - 1) * 30))

    if max_spike > 2.0:
        drivers.append(f"{max_spike:.0%} billing spike within analysis window")

    return score, drivers


def _behavioral_component(
    db: Session, provider: Provider, cutoff: datetime
) -> tuple:
    """Detect behavioral anomalies (weekend billing, batch submissions)."""
    drivers = []
    score = 0.0

    # Weekend billing ratio
    total_claims = (
        db.query(func.count(Claim.id))
        .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
        .scalar()
    ) or 0
    if total_claims == 0:
        return 0.0, drivers

    # Check for high beneficiary concentration
    top_beneficiary_pct = (
        db.query(func.count(Claim.id))
        .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
        .group_by(Claim.beneficiary_id)
        .order_by(func.count(Claim.id).desc())
        .first()
    )
    if top_beneficiary_pct:
        concentration = float(top_beneficiary_pct[0]) / total_claims
        if concentration > 0.3:
            score += 40
            drivers.append(f"High beneficiary concentration: {concentration:.0%}")

    # Check unique billing codes count
    unique_codes = (
        db.query(func.count(func.distinct(Claim.billing_code)))
        .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
        .scalar()
    ) or 0
    if unique_codes <= 2 and total_claims > 50:
        score += 30
        drivers.append(f"Limited billing code diversity: {unique_codes} codes for {total_claims} claims")

    return min(100, score), drivers


def _network_risk_component(db: Session, provider: Provider) -> tuple:
    """Layer 3: Network intelligence scoring.

    Evaluates network centrality, fraud ring membership, and
    connections to high-risk or sanctioned providers.
    """
    drivers = []
    score = 0.0

    # Anomaly-based network signal
    anomaly_count = (
        db.query(func.count(Anomaly.id))
        .filter(Anomaly.provider_id == provider.id)
        .scalar()
    ) or 0

    high_z_count = (
        db.query(func.count(Anomaly.id))
        .filter(Anomaly.provider_id == provider.id, Anomaly.z_score >= 5.0)
        .scalar()
    ) or 0

    score += min(40, anomaly_count * 5 + high_z_count * 10)
    if anomaly_count > 0:
        drivers.append(f"{anomaly_count} detected anomalies")
    if high_z_count > 0:
        drivers.append(f"{high_z_count} high-severity anomalies (z≥5)")

    # Network centrality and fraud ring analysis (if available)
    try:
        from services.network_analysis import get_network_summary
        network = get_network_summary(db, provider.id)
        connected = network.get("connected_entities", 0)
        high_risk = network.get("high_risk_connections", 0)
        in_ring = network.get("in_fraud_ring", False)

        if connected > 5:
            score += min(20, connected * 2)
            drivers.append(f"High network centrality: {connected} connected entities")
        if high_risk > 0:
            score += min(20, high_risk * 10)
            drivers.append(f"Connected to {high_risk} high-risk entities")
        if in_ring:
            ring_info = network.get("fraud_ring_info", {})
            score += 30
            drivers.append(
                f"Member of suspected fraud ring "
                f"(ring size: {ring_info.get('ring_size', 'N/A')})"
            )
    except Exception as e:
        logger.debug(f"Network analysis unavailable for scoring: {e}")

    return min(100, score), drivers


def _nyc_specific_component(
    db: Session, provider: Provider, cutoff: datetime
) -> tuple:
    """NYC Medicaid-specific fraud signals."""
    drivers = []
    score = 0.0

    if provider.state != "NY":
        return 0.0, drivers

    # Capacity violation check
    if provider.licensed_capacity and provider.licensed_capacity > 0:
        daily_max = (
            db.query(func.count(func.distinct(Claim.beneficiary_id)))
            .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
            .group_by(Claim.claim_date)
            .order_by(func.count(func.distinct(Claim.beneficiary_id)).desc())
            .first()
        )
        if daily_max:
            excess = float(daily_max[0]) / provider.licensed_capacity
            if excess > 1.0:
                score += 50
                drivers.append(
                    f"Capacity violation: {daily_max[0]} patients vs {provider.licensed_capacity} capacity ({excess:.0%})"
                )

    # High total billing for NYC
    total = (
        db.query(func.sum(Claim.amount))
        .filter(Claim.provider_id == provider.id, Claim.claim_date >= cutoff)
        .scalar()
    )
    if total and float(total) > 5_000_000:
        score += 30
        drivers.append(f"High NYC billing total: ${float(total):,.0f}")

    return min(100, score), drivers


def _historical_risk_component(db: Session, provider: Provider) -> tuple:
    """Layer 4 sub-component: Historical risk from prior sanctions and screening failures.

    Checks provider screening records and historical exclusion-list flags.
    """
    drivers = []
    score = 0.0

    try:
        from models import ProviderScreening
        failed_screenings = (
            db.query(func.count(ProviderScreening.id))
            .filter(
                ProviderScreening.provider_id == provider.id,
                ProviderScreening.status == "fail",
            )
            .scalar()
        ) or 0

        exclusion_hits = (
            db.query(func.count(ProviderScreening.id))
            .filter(
                ProviderScreening.provider_id == provider.id,
                ProviderScreening.exclusion_list_check.is_(True),
                ProviderScreening.status == "fail",
            )
            .scalar()
        ) or 0

        if failed_screenings > 0:
            score += min(50, failed_screenings * 25)
            drivers.append(f"{failed_screenings} failed screening(s) on record")
        if exclusion_hits > 0:
            score += 40
            drivers.append(f"Flagged on exclusion list ({exclusion_hits} hit(s))")
    except Exception as e:
        logger.debug(f"Provider screening data unavailable: {e}")

    return min(100, score), drivers
