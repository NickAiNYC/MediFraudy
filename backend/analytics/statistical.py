"""Statistical analysis for Medicaid billing data.

Provides z-score outlier detection, percentile analysis, and trend detection
optimized for large datasets (10M+ claims).
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, desc, asc
from sqlalchemy.sql import label
from scipy import stats
from sklearn.preprocessing import StandardScaler

from models import Claim, Provider, Anomaly

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core statistical functions
# ---------------------------------------------------------------------------

def calculate_billing_stats(
    db: Session,
    state: str = "NY",
    billing_code: Optional[str] = None,
    facility_type: Optional[str] = None,
    min_date: Optional[datetime] = None,
    max_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Calculate comprehensive billing statistics.

    Args:
        db: Database session.
        state: Two-letter state code to filter providers.
        billing_code: Optional billing code to filter claims.
        facility_type: Optional facility type filter.
        min_date: Optional minimum claim date.
        max_date: Optional maximum claim date.

    Returns:
        Dictionary of statistical measures including mean, median, percentiles.
    """
    # Build query
    query = (
        db.query(Claim.amount)
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
    )
    
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)
    
    if facility_type:
        query = query.filter(Provider.facility_type == facility_type)
    
    if min_date:
        query = query.filter(Claim.claim_date >= min_date)
    
    if max_date:
        query = query.filter(Claim.claim_date <= max_date)

    # Execute and convert to numpy
    amounts = [row[0] for row in query.all()]
    count = len(amounts)
    
    if count == 0:
        return {
            "mean": None,
            "median": None,
            "std_dev": None,
            "variance": None,
            "min": None,
            "max": None,
            "q1": None,
            "q3": None,
            "iqr": None,
            "skewness": None,
            "kurtosis": None,
            "count": 0,
            "state": state,
            "billing_code": billing_code,
            "facility_type": facility_type,
        }

    arr = np.array(amounts, dtype=float)
    
    # Calculate statistics
    stats_dict = {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std_dev": float(np.std(arr)),
        "variance": float(np.var(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "q1": float(np.percentile(arr, 25)),
        "q3": float(np.percentile(arr, 75)),
        "iqr": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
        "skewness": float(stats.skew(arr)),
        "kurtosis": float(stats.kurtosis(arr)),
        "count": count,
        "state": state,
        "billing_code": billing_code,
        "facility_type": facility_type,
        "total_amount": float(np.sum(arr)),
    }
    
    logger.debug(f"Calculated stats for {state}/{billing_code}: {stats_dict['count']} claims")
    return stats_dict


def detect_outliers_zscore(
    db: Session,
    z_threshold: float = 3.0,
    state: str = "NY",
    billing_code: Optional[str] = None,
    facility_type: Optional[str] = None,
    min_claims: int = 10,
    include_provider_details: bool = True,
) -> List[Dict[str, Any]]:
    """Identify providers whose average billing exceeds z_threshold.

    Args:
        db: Database session.
        z_threshold: Z-score cutoff for outlier detection.
        state: Two-letter state code.
        billing_code: Optional billing code filter.
        facility_type: Optional facility type filter.
        min_claims: Minimum number of claims required for inclusion.
        include_provider_details: Whether to include full provider info.

    Returns:
        List of outlier providers sorted by absolute z-score.
    """
    # Build query for provider averages
    query = (
        db.query(
            Provider.id,
            Provider.npi,
            Provider.name,
            Provider.facility_type,
            Provider.city,
            func.avg(Claim.amount).label("avg_amount"),
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
    )
    
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)
    
    if facility_type:
        query = query.filter(Provider.facility_type == facility_type)
    
    query = query.group_by(Provider.id).having(func.count(Claim.id) >= min_claims)
    rows = query.all()

    if not rows:
        return []

    # Extract averages for statistical calculation
    averages = np.array([float(r.avg_amount) for r in rows])
    mean = np.mean(averages)
    std = np.std(averages)

    if std == 0:
        logger.warning("Zero standard deviation in outlier detection")
        return []

    # Calculate z-scores and filter
    outliers = []
    for row, avg in zip(rows, averages):
        z = (avg - mean) / std
        if abs(z) >= z_threshold:
            outlier = {
                "provider_id": row.id,
                "avg_amount": float(avg),
                "z_score": float(z),
                "claim_count": int(row.claim_count),
                "total_amount": float(row.total_amount),
            }
            if include_provider_details:
                outlier.update({
                    "npi": row.npi,
                    "name": row.name,
                    "facility_type": row.facility_type,
                    "city": row.city,
                })
            outliers.append(outlier)

    # Sort by absolute z-score (highest first)
    outliers.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    
    logger.info(f"Detected {len(outliers)} outliers with z > {z_threshold}")
    return outliers


def detect_outliers_percentile(
    db: Session,
    percentile_threshold: float = 95.0,
    state: str = "NY",
    billing_code: Optional[str] = None,
    facility_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Identify providers above a percentile threshold.

    Alternative to z-score that's more robust for non-normal distributions.
    
    Args:
        db: Database session.
        percentile_threshold: Percentile cutoff (e.g., 95 = top 5%).
        state: Two-letter state code.
        billing_code: Optional billing code filter.
        facility_type: Optional facility type filter.

    Returns:
        List of outlier providers sorted by amount.
    """
    query = (
        db.query(
            Provider.id,
            Provider.npi,
            Provider.name,
            func.avg(Claim.amount).label("avg_amount"),
            func.count(Claim.id).label("claim_count"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
    )
    
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)
    
    if facility_type:
        query = query.filter(Provider.facility_type == facility_type)
    
    rows = query.group_by(Provider.id).all()
    
    if not rows:
        return []
    
    averages = np.array([float(r.avg_amount) for r in rows])
    threshold = np.percentile(averages, percentile_threshold)
    
    outliers = []
    for row, avg in zip(rows, averages):
        if avg >= threshold:
            outliers.append({
                "provider_id": row.id,
                "npi": row.npi,
                "name": row.name,
                "avg_amount": float(avg),
                "percentile": float(stats.percentileofscore(averages, avg)),
                "claim_count": int(row.claim_count),
            })
    
    outliers.sort(key=lambda x: x["avg_amount"], reverse=True)
    return outliers


def detect_yoy_trends(
    db: Session,
    state: str = "NY",
    billing_code: Optional[str] = None,
    facility_type: Optional[str] = None,
    provider_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Detect year-over-year billing trends with growth rates.

    Args:
        db: Database session.
        state: Two-letter state code.
        billing_code: Optional billing code filter.
        facility_type: Optional facility type filter.
        provider_id: Optional specific provider ID.

    Returns:
        List of yearly summaries with growth rates.
    """
    query = (
        db.query(
            extract("year", Claim.claim_date).label("year"),
            func.sum(Claim.amount).label("total"),
            func.count(Claim.id).label("claim_count"),
            func.avg(Claim.amount).label("average"),
        )
        .join(Provider, Claim.provider_id == Provider.id)
    )
    
    if provider_id:
        query = query.filter(Provider.id == provider_id)
    else:
        query = query.filter(Provider.state == state)
    
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)
    
    if facility_type:
        query = query.filter(Provider.facility_type == facility_type)
    
    rows = query.group_by("year").order_by("year").all()

    if not rows:
        return []

    # Calculate year-over-year growth
    results = []
    prev_total = None
    
    for r in rows:
        year_data = {
            "year": int(r.year),
            "total": float(r.total),
            "claim_count": int(r.claim_count),
            "average": float(r.average) if r.average else 0,
        }
        
        if prev_total is not None and prev_total > 0:
            year_data["growth_rate"] = float((r.total - prev_total) / prev_total * 100)
        else:
            year_data["growth_rate"] = None
            
        prev_total = r.total
        results.append(year_data)
    
    return results


def detect_seasonal_patterns(
    db: Session,
    state: str = "NY",
    billing_code: Optional[str] = None,
    years: int = 3,
) -> Dict[str, Any]:
    """Detect seasonal patterns in billing (monthly aggregates).

    Useful for identifying unusual seasonal variations.
    
    Args:
        db: Database session.
        state: Two-letter state code.
        billing_code: Optional billing code filter.
        years: Number of years to analyze.

    Returns:
        Dictionary with monthly statistics and anomalies.
    """
    cutoff_date = datetime.now() - timedelta(days=365 * years)
    
    query = (
        db.query(
            extract("month", Claim.claim_date).label("month"),
            func.avg(Claim.amount).label("avg_amount"),
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total"),
        )
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
        .filter(Claim.claim_date >= cutoff_date)
    )
    
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)
    
    rows = query.group_by("month").order_by("month").all()
    
    monthly_stats = {}
    all_avgs = []
    
    for r in rows:
        month = int(r.month)
        avg = float(r.avg_amount)
        monthly_stats[month] = {
            "average": avg,
            "total": float(r.total),
            "claim_count": int(r.claim_count),
        }
        all_avgs.append(avg)
    
    # Calculate overall statistics
    if all_avgs:
        overall_mean = np.mean(all_avgs)
        overall_std = np.std(all_avgs)
        
        # Flag anomalous months
        for month, stats in monthly_stats.items():
            z = (stats["average"] - overall_mean) / overall_std if overall_std > 0 else 0
            stats["z_score"] = float(z)
            stats["anomalous"] = abs(z) > 2.0
    
    return {
        "monthly_stats": monthly_stats,
        "overall_mean": float(overall_mean) if all_avgs else None,
        "overall_std": float(overall_std) if all_avgs else None,
    }


def detect_weekend_bias(
    db: Session,
    state: str = "NY",
    billing_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Detect unusual weekend billing patterns (Brooklyn case indicator).

    Args:
        db: Database session.
        state: Two-letter state code.
        billing_code: Optional billing code filter.

    Returns:
        Dictionary with weekend statistics.
    """
    query = (
        db.query(
            func.count(Claim.id).label("total"),
            func.sum(
                func.cast(
                    func.extract('dow', Claim.claim_date).in_([0, 6]),  # Sunday=0, Saturday=6
                    Integer
                )
            ).label("weekend_count"),
        )
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
    )
    
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)
    
    row = query.first()
    
    if not row or row.total == 0:
        return {"weekend_percentage": 0, "total_claims": 0}
    
    weekend_pct = (row.weekend_count / row.total) * 100
    
    return {
        "total_claims": int(row.total),
        "weekend_claims": int(row.weekend_count),
        "weekend_percentage": float(weekend_pct),
        "flagged": weekend_pct > 20,  # Flag if >20% weekend claims
    }


def save_anomalies(
    db: Session,
    outliers: List[Dict[str, Any]],
    anomaly_type: str = "statistical",
) -> int:
    """Save detected anomalies to database for dashboard display.

    Args:
        db: Database session.
        outliers: List of outlier dictionaries from detection functions.
        anomaly_type: Type of anomaly (statistical, pattern_of_life, etc.)

    Returns:
        Number of anomalies saved.
    """
    saved = 0
    for outlier in outliers:
        # Check if already exists (avoid duplicates)
        existing = db.query(Anomaly).filter(
            Anomaly.provider_id == outlier["provider_id"],
            Anomaly.billing_code == outlier.get("billing_code", "unknown"),
            Anomaly.anomaly_type == anomaly_type,
        ).first()
        
        if existing:
            continue
        
        anomaly = Anomaly(
            provider_id=outlier["provider_id"],
            billing_code=outlier.get("billing_code", "all"),
            z_score=outlier.get("z_score", 0),
            anomaly_type=anomaly_type,
            notes=json.dumps(outlier),
        )
        db.add(anomaly)
        saved += 1
    
    db.commit()
    logger.info(f"Saved {saved} new anomalies")
    return saved


# Alias for backward compatibility
detect_outliers = detect_outliers_zscore
