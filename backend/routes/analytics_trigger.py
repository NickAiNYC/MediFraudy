"""Analytics trigger routes — all missing /api/analytics/* endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db
from models import Provider, Claim, Beneficiary, EVVLog, TransportationTrip

router = APIRouter()


@router.get("/analytics/dashboard/summary", tags=["Analytics"])
def dashboard_summary(db: Session = Depends(get_db)):
    from models import Case
    provider_count = db.query(Provider).count()
    claim_count = db.query(Claim).count()
    total_billed = db.query(func.sum(Claim.amount)).scalar() or 0.0
    open_cases = db.query(Case).filter(Case.status == "open").count()
    return {
        "providers": provider_count,
        "claims": claim_count,
        "total_billed": round(total_billed, 2),
        "open_cases": open_cases,
        "currency": "USD",
    }


@router.get("/analytics/nemt/impossible-trips", tags=["Analytics"])
def nemt_impossible_trips(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    trips = (
        db.query(TransportationTrip)
        .filter(
            TransportationTrip.claimed_distance.isnot(None),
            TransportationTrip.calculated_distance.isnot(None),
            TransportationTrip.claimed_distance > TransportationTrip.calculated_distance * 1.5,
        )
        .limit(limit)
        .all()
    )
    results = []
    for t in trips:
        ratio = (
            round(t.claimed_distance / t.calculated_distance, 2)
            if t.calculated_distance and t.calculated_distance > 0
            else None
        )
        results.append({
            "trip_id": t.id,
            "claim_id": t.claim_id,
            "calculated_distance_miles": t.calculated_distance,
            "claimed_distance_miles": t.claimed_distance,
            "inflation_ratio": ratio,
            "is_group_ride": t.is_group_ride,
            "pickup": {"lat": t.pickup_lat, "lon": t.pickup_lon},
            "dropoff": {"lat": t.dropoff_lat, "lon": t.dropoff_lon},
        })
    return {"impossible_trips": results, "count": len(results)}


@router.get("/analytics/nemt/ghost-rides", tags=["Analytics"])
def nemt_ghost_rides(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    claims = (
        db.query(Claim)
        .join(TransportationTrip, TransportationTrip.claim_id == Claim.id)
        .filter(Claim.service_category.ilike("%transport%"))
        .limit(limit * 2)
        .all()
    )
    results = []
    for claim in claims:
        evv_exists = (
            db.query(EVVLog)
            .filter(
                EVVLog.beneficiary_id == claim.beneficiary_id,
                func.date(EVVLog.timestamp) == claim.claim_date,
            )
            .first()
        )
        if not evv_exists:
            results.append({
                "claim_id": claim.id,
                "beneficiary_id": claim.beneficiary_id,
                "claim_date": str(claim.claim_date),
                "amount": claim.amount,
                "billing_code": claim.billing_code,
                "evv_verified": False,
                "fraud_flag": "ghost_ride_no_evv",
            })
        if len(results) >= limit:
            break
    return {"ghost_rides": results, "count": len(results)}


@router.get("/analytics/recipient/reselling-meds", tags=["Analytics"])
def recipient_reselling_meds(
    min_pharmacies: int = Query(3, ge=2, le=20),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Claim.beneficiary_id,
            func.count(func.distinct(Claim.provider_id)).label("pharmacy_count"),
            func.sum(Claim.amount).label("total_spend"),
            func.count(Claim.id).label("claim_count"),
        )
        .filter(Claim.service_category.ilike("%pharm%"))
        .group_by(Claim.beneficiary_id)
        .having(func.count(func.distinct(Claim.provider_id)) >= min_pharmacies)
        .order_by(func.count(func.distinct(Claim.provider_id)).desc())
        .all()
    )
    return {
        "reselling_suspects": [
            {
                "beneficiary_id": r.beneficiary_id,
                "distinct_pharmacies": r.pharmacy_count,
                "total_spend": round(r.total_spend or 0, 2),
                "claim_count": r.claim_count,
                "risk_flag": "multi_pharmacy_recipient",
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/analytics/recipient/card-sharing", tags=["Analytics"])
def recipient_card_sharing(
    min_dist: float = Query(50.0, ge=1.0),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Claim.beneficiary_id,
            Claim.claim_date,
            func.count(func.distinct(Claim.provider_id)).label("provider_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .group_by(Claim.beneficiary_id, Claim.claim_date)
        .having(func.count(func.distinct(Claim.provider_id)) >= 2)
        .order_by(func.count(func.distinct(Claim.provider_id)).desc())
        .limit(200)
        .all()
    )
    return {
        "card_sharing_suspects": [
            {
                "beneficiary_id": r.beneficiary_id,
                "date": str(r.claim_date),
                "providers_same_day": r.provider_count,
                "total_amount": round(r.total_amount or 0, 2),
                "risk_flag": "card_sharing_multi_provider",
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/analytics/sadc/attendance-heatmap", tags=["Analytics"])
def sadc_attendance_heatmap(
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Claim.provider_id,
            Provider.name.label("provider_name"),
            Provider.city,
            Claim.claim_date,
            func.count(func.distinct(Claim.beneficiary_id)).label("patient_count"),
            func.sum(Claim.amount).label("day_total"),
        )
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Provider.facility_type.ilike("%adult day%"))
        .group_by(Claim.provider_id, Provider.name, Provider.city, Claim.claim_date)
        .order_by(func.count(func.distinct(Claim.beneficiary_id)).desc())
        .limit(limit)
        .all()
    )
    return {
        "heatmap": [
            {
                "provider_id": r.provider_id,
                "provider_name": r.provider_name,
                "city": r.city,
                "date": str(r.claim_date),
                "patient_count": r.patient_count,
                "day_total": round(r.day_total or 0, 2),
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/analytics/pharmacy/lidocaine-dumping", tags=["Analytics"])
def pharmacy_lidocaine_dumping(
    threshold: int = Query(1000, ge=100),
    db: Session = Depends(get_db),
):
    LIDOCAINE_CODES = ["J2001", "J3490", "J3590", "99999"]
    rows = (
        db.query(
            Claim.provider_id,
            Provider.name.label("provider_name"),
            Provider.city,
            Claim.billing_code,
            func.sum(Claim.units).label("total_units"),
            func.sum(Claim.amount).label("total_billed"),
            func.count(Claim.id).label("claim_count"),
        )
        .join(Provider, Claim.provider_id == Provider.id)
        .filter(Claim.billing_code.in_(LIDOCAINE_CODES))
        .group_by(Claim.provider_id, Provider.name, Provider.city, Claim.billing_code)
        .having(func.sum(Claim.units) >= threshold)
        .order_by(func.sum(Claim.units).desc())
        .all()
    )
    return {
        "lidocaine_dumping_suspects": [
            {
                "provider_id": r.provider_id,
                "provider_name": r.provider_name,
                "city": r.city,
                "billing_code": r.billing_code,
                "total_units": r.total_units,
                "total_billed": round(r.total_billed or 0, 2),
                "claim_count": r.claim_count,
                "risk_flag": "excessive_lidocaine_billing",
            }
            for r in rows
        ],
        "count": len(rows),
        "unit_threshold": threshold,
    }


@router.get("/analytics/cdpap/network", tags=["Analytics"])
def cdpap_network(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Provider.id,
            Provider.name,
            Provider.city,
            Provider.npi,
            func.count(Claim.id).label("claim_count"),
            func.count(func.distinct(Claim.beneficiary_id)).label("patient_count"),
            func.sum(Claim.amount).label("total_billed"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(
            Provider.facility_type.ilike("%cdpap%")
            | Provider.specialty.ilike("%cdpap%")
        )
        .group_by(Provider.id, Provider.name, Provider.city, Provider.npi)
        .order_by(func.sum(Claim.amount).desc())
        .limit(limit)
        .all()
    )
    return {
        "cdpap_providers": [
            {
                "provider_id": r.id,
                "name": r.name,
                "city": r.city,
                "npi": r.npi,
                "claim_count": r.claim_count,
                "patient_count": r.patient_count,
                "total_billed": round(r.total_billed or 0, 2),
            }
            for r in rows
        ],
        "count": len(rows),
    }
