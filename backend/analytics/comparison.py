"""Provider peer comparison analytics.

Compares individual providers against peer groups to identify outliers
and generate statistical evidence for fraud cases.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import numpy as np
from scipy import stats
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models import Provider, Claim

logger = logging.getLogger(__name__)


def compare_provider_to_peers(
    db: Session, 
    provider_id: int,
    days_back: Optional[int] = 365,
    include_percentiles: bool = True,
    include_trend: bool = False
) -> Dict[str, Any]:
    """Compare a single provider's billing to peer averages.

    Peers are defined as providers with the same facility_type in the same state,
    optionally filtered by region and size.

    Args:
        db: Database session.
        provider_id: ID of the provider to compare.
        days_back: Number of days to analyze (None for all time).
        include_percentiles: Whether to include percentile rankings.
        include_trend: Whether to include trend comparison.

    Returns:
        Dictionary with provider stats and peer group stats.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}

    # Build date filter
    date_filter = []
    if days_back:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        date_filter = [Claim.claim_date >= cutoff_date]

    # Provider's own stats
    provider_stats = (
        db.query(
            func.avg(Claim.amount).label("avg_amount"),
            func.sum(Claim.amount).label("total_amount"),
            func.count(Claim.id).label("claim_count"),
            func.count(func.distinct(Claim.beneficiary_id)).label("unique_patients"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(*date_filter)
        .first()
    )

    if not provider_stats or not provider_stats.claim_count:
        return {
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "facility_type": provider.facility_type,
                "city": provider.city,
                "state": provider.state,
            },
            "peer_group": {"count": 0, "avg_amount": None, "std_dev": None},
            "z_score": None,
            "message": "No claims data for provider in selected period"
        }

    # Define peer groups (increasingly specific)
    peer_groups = {
        "state_type": _get_peer_group(db, provider, "state_type", date_filter),
        "region_type": _get_peer_group(db, provider, "region_type", date_filter),
    }

    # Calculate provider metrics
    prov_avg = float(provider_stats.avg_amount or 0)
    prov_total = float(provider_stats.total_amount or 0)
    prov_count = int(provider_stats.claim_count or 0)
    prov_patients = int(provider_stats.unique_patients or 0)
    prov_per_patient = prov_total / prov_patients if prov_patients > 0 else 0

    # Build response
    response = {
        "provider": {
            "id": provider.id,
            "npi": provider.npi,
            "name": provider.name,
            "facility_type": provider.facility_type,
            "city": provider.city,
            "state": provider.state,
            "licensed_capacity": provider.licensed_capacity,
            "avg_claim_amount": round(prov_avg, 2),
            "total_billed": round(prov_total, 2),
            "claim_count": prov_count,
            "unique_patients": prov_patients,
            "avg_per_patient": round(prov_per_patient, 2),
        },
        "analysis_period_days": days_back,
        "peer_comparisons": {},
    }

    # Add each peer group comparison
    for group_name, peer_data in peer_groups.items():
        if peer_data["count"] < 2:
            response["peer_comparisons"][group_name] = {
                "count": peer_data["count"],
                "message": "Insufficient peers for comparison"
            }
            continue

        peer_avgs = np.array(peer_data["avgs"])
        peer_mean = float(np.mean(peer_avgs))
        peer_std = float(np.std(peer_avgs)) if len(peer_avgs) > 1 else 0
        peer_median = float(np.median(peer_avgs))
        peer_min = float(np.min(peer_avgs))
        peer_max = float(np.max(peer_avgs))

        # Calculate z-score
        z_score = (prov_avg - peer_mean) / peer_std if peer_std > 0 else 0.0

        # Calculate percentile rank
        percentile = stats.percentileofscore(peer_avgs, prov_avg) if include_percentiles else None

        # Calculate additional metrics
        above_average_pct = (prov_avg - peer_mean) / peer_mean * 100 if peer_mean > 0 else 0

        comparison = {
            "count": peer_data["count"],
            "mean": round(peer_mean, 2),
            "median": round(peer_median, 2),
            "std_dev": round(peer_std, 2),
            "min": round(peer_min, 2),
            "max": round(peer_max, 2),
            "provider_z_score": round(z_score, 3),
            "provider_percentile": round(percentile, 1) if percentile else None,
            "above_average_percentage": round(above_average_pct, 1),
            "is_outlier": abs(z_score) > 3,
            "is_moderate_outlier": abs(z_score) > 2,
        }

        # Add peer patient metrics if available
        if peer_data.get("patient_avgs"):
            patient_avgs = np.array(peer_data["patient_avgs"])
            patient_mean = float(np.mean(patient_avgs))
            patient_std = float(np.std(patient_avgs)) if len(patient_avgs) > 1 else 0
            
            comparison["peer_patients"] = {
                "mean": round(patient_mean, 2),
                "std_dev": round(patient_std, 2),
            }
            comparison["provider_patients"] = prov_patients
            
            # Patient volume z-score
            if patient_std > 0:
                patient_z = (prov_patients - patient_mean) / patient_std
                comparison["patient_z_score"] = round(patient_z, 3)
                comparison["patient_outlier"] = abs(patient_z) > 3

        response["peer_comparisons"][group_name] = comparison

    # Add trend comparison if requested
    if include_trend:
        response["trend_analysis"] = _compare_trends(db, provider_id, date_filter)

    return response


def _get_peer_group(
    db: Session,
    provider: Provider,
    group_type: str,
    date_filter: List
) -> Dict[str, Any]:
    """Get peer group data for a provider.

    Args:
        db: Database session
        provider: Provider object
        group_type: "state_type" or "region_type"
        date_filter: SQLAlchemy date filters

    Returns:
        Dictionary with peer group data
    """
    # Build base query
    query = (
        db.query(
            Provider.id,
            func.avg(Claim.amount).label("avg_amount"),
            func.sum(Claim.amount).label("total_amount"),
            func.count(Claim.id).label("claim_count"),
            func.count(func.distinct(Claim.beneficiary_id)).label("unique_patients"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(*date_filter)
        .filter(Provider.id != provider.id)
    )

    # Apply peer group filters
    if group_type == "state_type":
        query = query.filter(
            Provider.facility_type == provider.facility_type,
            Provider.state == provider.state,
        )
    elif group_type == "region_type":
        # Same facility type and region (first 3 digits of zip or same city)
        if provider.zip_code and len(provider.zip_code) >= 3:
            zip_prefix = provider.zip_code[:3] + "%"
            query = query.filter(
                Provider.facility_type == provider.facility_type,
                Provider.zip_code.like(zip_prefix)
            )
        else:
            # Fallback to same city
            query = query.filter(
                Provider.facility_type == provider.facility_type,
                Provider.city == provider.city
            )

    # Group by provider
    query = query.group_by(Provider.id)
    rows = query.all()

    if not rows:
        return {"count": 0, "avgs": [], "patient_avgs": []}

    # Extract averages
    avgs = [float(r.avg_amount) for r in rows if r.avg_amount]
    patient_avgs = [float(r.unique_patients) for r in rows if r.unique_patients]

    return {
        "count": len(rows),
        "avgs": avgs,
        "patient_avgs": patient_avgs,
    }


def _compare_trends(
    db: Session,
    provider_id: int,
    date_filter: List
) -> Dict[str, Any]:
    """Compare provider's billing trend to peer trends.

    Args:
        db: Database session
        provider_id: Provider ID
        date_filter: SQLAlchemy date filters

    Returns:
        Trend comparison data
    """
    # Get provider's monthly totals
    provider_monthly = (
        db.query(
            func.strftime('%Y-%m', Claim.claim_date).label("month"),
            func.sum(Claim.amount).label("total"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(*date_filter)
        .group_by(func.strftime('%Y-%m', Claim.claim_date))
        .order_by(func.strftime('%Y-%m', Claim.claim_date))
        .all()
    )

    if len(provider_monthly) < 3:
        return {"message": "Insufficient data for trend analysis"}

    # Calculate growth rate
    provider_totals = [float(r.total) for r in provider_monthly]
    first_3_avg = sum(provider_totals[:3]) / 3
    last_3_avg = sum(provider_totals[-3:]) / 3
    growth_rate = ((last_3_avg - first_3_avg) / first_3_avg * 100) if first_3_avg > 0 else 0

    return {
        "months_analyzed": len(provider_monthly),
        "first_3_month_avg": round(first_3_avg, 2),
        "last_3_month_avg": round(last_3_avg, 2),
        "growth_rate_percent": round(growth_rate, 1),
        "is_rapid_growth": growth_rate > 50,
    }


def batch_compare_providers(
    db: Session,
    provider_ids: List[int],
    days_back: Optional[int] = 365
) -> List[Dict[str, Any]]:
    """Compare multiple providers in batch.

    Args:
        db: Database session
        provider_ids: List of provider IDs
        days_back: Number of days to analyze

    Returns:
        List of comparison results
    """
    results = []
    for provider_id in provider_ids:
        try:
            result = compare_provider_to_peers(db, provider_id, days_back, include_percentiles=True)
            results.append(result)
        except Exception as e:
            logger.error(f"Error comparing provider {provider_id}: {e}")
            results.append({
                "provider_id": provider_id,
                "error": str(e)
            })
    
    return results


def get_peer_outliers(
    db: Session,
    facility_type: str,
    state: str = "NY",
    z_threshold: float = 3.0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get providers that are outliers compared to their peers.

    Args:
        db: Database session
        facility_type: Type of facility to analyze
        state: State code
        z_threshold: Z-score threshold for outlier detection
        limit: Maximum number of results

    Returns:
        List of outlier providers with their z-scores
    """
    # Get all providers of this type
    providers = (
        db.query(Provider)
        .filter(
            Provider.facility_type == facility_type,
            Provider.state == state
        )
        .limit(limit)
        .all()
    )

    outliers = []
    for provider in providers:
        comparison = compare_provider_to_peers(db, provider.id, include_percentiles=False)
        
        # Check each peer group for outliers
        for group_name, group_data in comparison.get("peer_comparisons", {}).items():
            if isinstance(group_data, dict) and group_data.get("is_outlier"):
                outliers.append({
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                    "facility_type": facility_type,
                    "city": provider.city,
                    "peer_group": group_name,
                    "z_score": group_data.get("provider_z_score"),
                    "above_average_pct": group_data.get("above_average_percentage"),
                    "avg_amount": comparison["provider"]["avg_claim_amount"],
                    "peer_avg": group_data.get("mean"),
                })
                break  # Found one outlier group, move to next provider

    # Sort by z-score (highest first)
    outliers.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    
    return outliers
