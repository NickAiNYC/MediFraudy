"""Data validation API routes.

Provides endpoints for data quality checks, schema validation,
and data quality report generation.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import get_db
from models import Provider, Claim, Anomaly

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-quality", tags=["data-quality"])


@router.get("/report")
def get_data_quality_report(db: Session = Depends(get_db)):
    """Generate a data quality report for the current database.

    Returns metrics on record counts, null rates, duplicate rates,
    and data freshness for core tables.
    """
    report = {
        "tables": {},
        "overall_health": "healthy",
        "issues": [],
    }

    # Provider quality
    provider_count = db.query(func.count(Provider.id)).scalar() or 0
    provider_nulls = {
        "npi_nulls": db.query(func.count(Provider.id)).filter(Provider.npi.is_(None)).scalar() or 0,
        "name_nulls": db.query(func.count(Provider.id)).filter(Provider.name.is_(None)).scalar() or 0,
        "state_nulls": db.query(func.count(Provider.id)).filter(Provider.state.is_(None)).scalar() or 0,
    }
    report["tables"]["providers"] = {
        "total_records": provider_count,
        "null_checks": provider_nulls,
    }

    # Claim quality
    claim_count = db.query(func.count(Claim.id)).scalar() or 0
    if claim_count > 0:
        negative_amounts = db.query(func.count(Claim.id)).filter(Claim.amount < 0).scalar() or 0
        null_billing = db.query(func.count(Claim.id)).filter(Claim.billing_code.is_(None)).scalar() or 0
        null_dates = db.query(func.count(Claim.id)).filter(Claim.claim_date.is_(None)).scalar() or 0
        duplicate_claims = claim_count - (
            db.query(func.count(func.distinct(Claim.claim_id))).scalar() or 0
        )

        report["tables"]["claims"] = {
            "total_records": claim_count,
            "negative_amounts": negative_amounts,
            "null_billing_codes": null_billing,
            "null_dates": null_dates,
            "potential_duplicates": max(0, duplicate_claims),
        }

        # Flag issues
        if negative_amounts > 0:
            report["issues"].append(
                f"{negative_amounts} claims have negative amounts"
            )
        if null_billing > 0:
            report["issues"].append(
                f"{null_billing} claims missing billing codes"
            )
        if duplicate_claims > 0:
            report["issues"].append(
                f"{duplicate_claims} potential duplicate claim IDs"
            )
    else:
        report["tables"]["claims"] = {"total_records": 0}

    # Anomaly quality
    anomaly_count = db.query(func.count(Anomaly.id)).scalar() or 0
    report["tables"]["anomalies"] = {"total_records": anomaly_count}

    # Overall health
    if len(report["issues"]) > 3:
        report["overall_health"] = "degraded"
    elif len(report["issues"]) > 0:
        report["overall_health"] = "warning"

    return report


@router.get("/freshness")
def get_data_freshness(db: Session = Depends(get_db)):
    """Check data freshness — when was data last updated."""
    freshness = {}

    latest_provider = (
        db.query(func.max(Provider.created_at)).scalar()
    )
    freshness["providers"] = {
        "latest_record": str(latest_provider) if latest_provider else None,
    }

    latest_claim = (
        db.query(func.max(Claim.claim_date)).scalar()
    )
    freshness["claims"] = {
        "latest_claim_date": str(latest_claim) if latest_claim else None,
    }

    latest_anomaly = (
        db.query(func.max(Anomaly.detected_at)).scalar()
    )
    freshness["anomalies"] = {
        "latest_detection": str(latest_anomaly) if latest_anomaly else None,
    }

    return freshness
