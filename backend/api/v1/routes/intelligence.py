"""Risk scoring and fraud intelligence API routes.

Provides:
- Individual provider risk scoring
- Batch risk scoring
- Evidence package generation
- Anomaly detection endpoints
- NYC-specific fraud signals
- Borough heatmap data
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.risk_scoring import calculate_risk_score, batch_risk_scores
from services.evidence_builder import generate_case_package
from services.anomaly_engine import (
    detect_billing_spikes,
    detect_impossible_service_density,
    detect_duplicate_claims,
    detect_billing_after_death,
)
from services.fraud_detection import (
    detect_homecare_inflation,
    detect_dme_abuse,
    detect_high_frequency_cpt,
    borough_risk_heatmap,
    cross_borough_referral_analysis,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


# --- Risk Scoring ---

@router.get("/risk-score/{provider_id}")
def get_risk_score(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Calculate composite fraud risk score for a provider.

    Returns weighted 0-100 score with risk drivers.

    Scoring bands:
    - 0–40: Low risk
    - 40–70: Review recommended
    - 70–100: High litigation risk
    """
    result = calculate_risk_score(db, provider_id, lookback_days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/risk-scores/batch")
def get_batch_risk_scores(
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Calculate risk scores for top providers by claim volume.

    Returns sorted list of providers with risk scores above min_score.
    """
    return {
        "results": batch_risk_scores(db, min_score=min_score, limit=limit),
        "analyzed_at": datetime.utcnow().isoformat(),
    }


# --- Evidence Builder ---

@router.get("/evidence-package/{provider_id}")
def get_evidence_package(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Generate litigation-ready evidence package for a provider.

    Includes:
    - Risk assessment with drivers
    - Statistical peer comparison
    - Timeline of suspicious activity
    - Claim breakdown by code
    - Network analysis summary
    - Auto-generated litigation narrative
    """
    result = generate_case_package(db, provider_id, lookback_days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --- Anomaly Detection ---

@router.get("/anomalies/billing-spikes/{provider_id}")
def get_billing_spikes(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    spike_threshold: float = Query(2.0, ge=1.0, le=10.0),
    db: Session = Depends(get_db),
):
    """Detect sudden billing volume spikes per CPT code."""
    return detect_billing_spikes(db, provider_id, lookback_days, spike_threshold)


@router.get("/anomalies/impossible-density/{provider_id}")
def get_impossible_density(
    provider_id: int,
    max_daily: int = Query(50, ge=10, le=200),
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect days with physically impossible service density."""
    return detect_impossible_service_density(db, provider_id, max_daily, lookback_days)


@router.get("/anomalies/duplicate-claims/{provider_id}")
def get_duplicate_claims(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect potential duplicate claims (same beneficiary, code, date)."""
    return detect_duplicate_claims(db, provider_id, lookback_days)


@router.get("/anomalies/billing-after-death/{provider_id}")
def get_billing_after_death(
    provider_id: int,
    db: Session = Depends(get_db),
):
    """Detect claims submitted for deceased beneficiaries."""
    return detect_billing_after_death(db, provider_id)


# --- NYC-Specific Fraud Signals ---

@router.get("/nyc/homecare-inflation/{provider_id}")
def get_homecare_inflation(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect inflated home care billing patterns."""
    return detect_homecare_inflation(db, provider_id, lookback_days)


@router.get("/nyc/dme-abuse/{provider_id}")
def get_dme_abuse(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect Durable Medical Equipment abuse patterns."""
    return detect_dme_abuse(db, provider_id, lookback_days)


@router.get("/nyc/cpt-overuse/{provider_id}")
def get_cpt_overuse(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    frequency_threshold: float = Query(3.0, ge=1.5, le=10.0),
    db: Session = Depends(get_db),
):
    """Detect CPT codes used at abnormally high frequency vs peers."""
    return detect_high_frequency_cpt(db, provider_id, lookback_days, frequency_threshold)


@router.get("/nyc/borough-heatmap")
def get_borough_heatmap(
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Generate risk heatmap data by NYC borough."""
    return borough_risk_heatmap(db, lookback_days)


@router.get("/nyc/cross-borough-referrals")
def get_cross_borough_referrals(
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect cross-borough referral patterns that may indicate fraud rings."""
    return cross_borough_referral_analysis(db, lookback_days)
