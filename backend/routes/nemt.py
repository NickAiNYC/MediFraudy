from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Provider, Claim
from analytics.nemt_detector import NEMTFraudDetector

router = APIRouter(
    prefix="/api/nemt",
    tags=["nemt"],
    responses={404: {"description": "Not found"}},
)

@router.get("/eligibility/{provider_id}")
def check_eligibility(provider_id: int, db: Session = Depends(get_db)):
    """Check for deceased/incarcerated beneficiaries for a provider."""
    detector = NEMTFraudDetector(db)
    df = detector.check_beneficiary_eligibility(provider_id)
    return {"suspicious_claims": df.to_dict(orient="records")}

@router.get("/ghost-rides/{provider_id}")
def check_ghost_rides(provider_id: int, db: Session = Depends(get_db)):
    """Check for transport claims without medical correlation."""
    detector = NEMTFraudDetector(db)
    df = detector.check_medical_correlation(provider_id)
    return {"ghost_rides": df.to_dict(orient="records")}

@router.get("/geographic-anomalies/{provider_id}")
def check_geo_anomalies(provider_id: int, db: Session = Depends(get_db)):
    """Check for mileage inflation and impossible routes."""
    detector = NEMTFraudDetector(db)
    df = detector.analyze_geographic_anomalies(provider_id)
    return {"anomalies": df.to_dict(orient="records")}

@router.get("/group-unbundling/{provider_id}")
def check_group_unbundling(provider_id: int, db: Session = Depends(get_db)):
    """Check for unbundled group rides."""
    detector = NEMTFraudDetector(db)
    df = detector.detect_group_ride_unbundling(provider_id)
    return {"potential_unbundling": df.to_dict(orient="records")}

@router.get("/milk-runs/{provider_id}")
def check_milk_runs(provider_id: int, db: Session = Depends(get_db)):
    """Check for milk runs (bringing multiple patients to a hub)."""
    detector = NEMTFraudDetector(db)
    df = detector.detect_milk_runs(provider_id)
    return {"milk_runs": df.to_dict(orient="records")}

@router.get("/risk-score/{provider_id}")
def get_risk_score(provider_id: int, db: Session = Depends(get_db)):
    """Get composite NEMT risk score."""
    detector = NEMTFraudDetector(db)
    score = detector.generate_nemt_risk_score(provider_id)
    return {"provider_id": provider_id, "risk_score": score}

@router.get("/high-risk-beneficiaries")
def get_high_risk_beneficiaries(limit: int = 100, db: Session = Depends(get_db)):
    """Get beneficiaries involved in multiple fraud schemes."""
    detector = NEMTFraudDetector(db)
    beneficiaries = detector.flag_high_risk_beneficiaries()
    return {"beneficiaries": [b.id for b in beneficiaries]} # Return IDs for now
