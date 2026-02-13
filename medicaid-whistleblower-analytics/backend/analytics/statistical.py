"""Statistical analysis for Medicaid billing data."""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from models import Claim, Provider

logger = logging.getLogger(__name__)


def calculate_billing_stats(
    db: Session,
    state: str = "NY",
    billing_code: Optional[str] = None,
) -> dict:
    """Calculate mean, median, and standard deviation for billing amounts.

    Args:
        db: Database session.
        state: Two-letter state code to filter providers.
        billing_code: Optional billing code to filter claims.

    Returns:
        Dictionary of statistical measures.
    """
    query = (
        db.query(Claim.amount)
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
    )
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)

    amounts = [row[0] for row in query.all()]
    if not amounts:
        return {"mean": None, "median": None, "std_dev": None, "count": 0}

    arr = np.array(amounts, dtype=float)
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std_dev": float(np.std(arr)),
        "count": len(arr),
    }


def detect_outliers(
    db: Session,
    z_threshold: float = 3.0,
    state: str = "NY",
) -> list[dict]:
    """Identify providers whose average billing is z_threshold standard deviations from the mean.

    Args:
        db: Database session.
        z_threshold: Z-score cutoff for outlier detection.
        state: Two-letter state code.

    Returns:
        List of outlier provider summaries.
    """
    rows = (
        db.query(
            Provider.id,
            Provider.npi,
            Provider.name,
            func.avg(Claim.amount).label("avg_amount"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
        .group_by(Provider.id)
        .all()
    )

    if not rows:
        return []

    averages = np.array([float(r.avg_amount) for r in rows])
    mean = np.mean(averages)
    std = np.std(averages)

    if std == 0:
        return []

    outliers = []
    for row, avg in zip(rows, averages):
        z = (avg - mean) / std
        if abs(z) >= z_threshold:
            outliers.append({
                "provider_id": row.id,
                "npi": row.npi,
                "name": row.name,
                "avg_amount": float(avg),
                "z_score": float(z),
            })

    outliers.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return outliers


def detect_yoy_trends(
    db: Session,
    state: str = "NY",
    billing_code: Optional[str] = None,
) -> list[dict]:
    """Detect year-over-year billing trends.

    Args:
        db: Database session.
        state: Two-letter state code.
        billing_code: Optional billing code filter.

    Returns:
        List of yearly summary dicts with total, count, and average.
    """
    query = (
        db.query(
            extract("year", Claim.claim_date).label("year"),
            func.sum(Claim.amount).label("total"),
            func.count(Claim.id).label("claim_count"),
        )
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Provider.state == state)
    )
    if billing_code:
        query = query.filter(Claim.billing_code == billing_code)

    rows = query.group_by("year").order_by("year").all()

    return [
        {
            "year": int(r.year),
            "total": float(r.total),
            "claim_count": int(r.claim_count),
            "average": float(r.total) / int(r.claim_count) if r.claim_count else 0,
        }
        for r in rows
    ]
