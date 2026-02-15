"""Impossible Patterns Detector for Medicaid fraud detection.

Detects physically, medically, and temporally impossible scenarios that
are strong indicators of fraudulent billing:

- Geospatial impossibility: simultaneous claims at distant locations,
  impossible provider travel between service sites.
- Clinical impossibility: duplicate incompatible procedures, age- or
  gender-inappropriate care, excessive service frequency.
- Temporal impossibility: billing for deceased patients, services before
  provider registration, claims submitted before service date, and
  providers billing more than 24 hours of services in a single day.

Uses existing ORM models (Provider, Claim, Beneficiary) and works with
both SQLite and PostgreSQL backends.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
from sqlalchemy import func, and_, text
from sqlalchemy.orm import Session

from models import Provider, Claim, Beneficiary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Billing codes considered incompatible when duplicated on the same patient
# on the same day (major surgeries that cannot reasonably be performed twice)
INCOMPATIBLE_DUPLICATE_CODES = {
    "27447",  # Total knee replacement
    "27130",  # Total hip replacement
    "33533",  # CABG (coronary artery bypass)
    "44150",  # Total colectomy
    "43239",  # Upper GI endoscopy with biopsy
    "47562",  # Laparoscopic cholecystectomy
}

# Pediatric-only billing code prefixes (99381–99385 well-child visits)
PEDIATRIC_CODE_PREFIXES = ("99381", "99382", "99383", "99384", "99385")

# Gender-specific procedure codes
MALE_ONLY_CODES = {
    "55840",  # Prostatectomy
    "55866",  # Laparoscopic prostatectomy
    "54150",  # Circumcision
}
FEMALE_ONLY_CODES = {
    "58150",  # Total hysterectomy
    "58661",  # Laparoscopic removal of adnexa
    "59400",  # Obstetric care (vaginal delivery)
    "59510",  # Cesarean delivery
}

# Reasonable annual maximum for common visit types
EXCESSIVE_FREQUENCY_THRESHOLDS = {
    "99395": 4,    # Preventive visit (annual) — 4 is generous
    "99396": 4,    # Preventive visit
    "99213": 52,   # Office visit (weekly max reasonable)
    "99214": 52,   # Office visit
    "99215": 26,   # Complex office visit (biweekly max)
}

# Default assumed service duration per unit in hours
DEFAULT_HOURS_PER_UNIT = 0.25  # 15-minute increments


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def detect_impossible_patterns(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Run all impossible-pattern checks for a provider.

    Combines geospatial, clinical, and temporal impossibility detection
    into a single report with a composite impossibility score (0–100).

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Number of days to look back (default 1 year).

    Returns:
        Dictionary with all sub-analysis results and composite score.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        logger.warning("Provider %d not found", provider_id)
        return {"error": "Provider not found", "impossibility_score": 0}

    geospatial = detect_geospatial_impossibility(db, provider_id, lookback_days)
    clinical = detect_clinical_impossibility(db, provider_id, lookback_days)
    temporal = detect_temporal_impossibility(db, provider_id, lookback_days)

    score = _compute_impossibility_score(geospatial, clinical, temporal)

    logger.info(
        "Impossible-pattern analysis for provider %d: score=%d",
        provider_id, score,
    )

    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "lookback_days": lookback_days,
        "impossibility_score": score,
        "geospatial": geospatial,
        "clinical": clinical,
        "temporal": temporal,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Geospatial impossibility
# ---------------------------------------------------------------------------

def detect_geospatial_impossibility(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect impossible travel or simultaneous multi-location claims.

    Checks two scenarios:
    1. A provider billing at different ``place_of_service`` locations
       on the same day where the implied travel is physically impossible.
    2. A patient (beneficiary) receiving care at two distinct locations
       on the same day from this provider.

    Because the Claim model stores ``place_of_service`` as a text field
    rather than coordinates, we detect *distinct* place-of-service values
    on the same day.  True geospatial validation requires geocoding (not
    available in the base schema), so we flag the anomaly and delegate
    distance verification to downstream investigation.

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with flagged days, simultaneous patient locations,
        and a geospatial risk score (0–100).
    """
    cutoff = datetime.utcnow().date() - timedelta(days=lookback_days)

    # --- Provider multi-location days ---
    rows = (
        db.query(
            Claim.claim_date,
            Claim.place_of_service,
            func.count(Claim.id).label("claim_count"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .filter(Claim.place_of_service.isnot(None))
        .group_by(Claim.claim_date, Claim.place_of_service)
        .order_by(Claim.claim_date)
        .all()
    )

    day_locations: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        d = str(r.claim_date)
        day_locations.setdefault(d, []).append({
            "place_of_service": r.place_of_service,
            "claim_count": int(r.claim_count),
        })

    multi_location_days: List[Dict[str, Any]] = [
        {"date": d, "locations": locs}
        for d, locs in day_locations.items()
        if len(locs) > 1
    ]

    # --- Patient simultaneous locations ---
    patient_rows = (
        db.query(
            Claim.beneficiary_id,
            Claim.claim_date,
            Claim.place_of_service,
            func.count(Claim.id).label("claim_count"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .filter(Claim.place_of_service.isnot(None))
        .filter(Claim.beneficiary_id.isnot(None))
        .group_by(Claim.beneficiary_id, Claim.claim_date, Claim.place_of_service)
        .order_by(Claim.claim_date)
        .all()
    )

    patient_day_locations: Dict[Tuple[str, str], List[str]] = {}
    for r in patient_rows:
        key = (str(r.beneficiary_id), str(r.claim_date))
        patient_day_locations.setdefault(key, []).append(r.place_of_service)

    simultaneous_patient_locations: List[Dict[str, Any]] = [
        {
            "beneficiary_id": k[0],
            "date": k[1],
            "locations": locs,
        }
        for k, locs in patient_day_locations.items()
        if len(set(locs)) > 1
    ]

    # Risk scoring
    risk = 0
    if multi_location_days:
        risk += min(50, len(multi_location_days) * 5)
    if simultaneous_patient_locations:
        risk += min(50, len(simultaneous_patient_locations) * 10)
    risk = min(100, risk)

    return {
        "multi_location_days": multi_location_days[:20],
        "multi_location_day_count": len(multi_location_days),
        "simultaneous_patient_locations": simultaneous_patient_locations[:20],
        "simultaneous_patient_count": len(simultaneous_patient_locations),
        "geospatial_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Clinical impossibility
# ---------------------------------------------------------------------------

def detect_clinical_impossibility(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect medically impossible billing patterns.

    Checks:
    1. Duplicate incompatible procedures on the same patient/day.
    2. Excessive frequency of a single service type for a beneficiary.
    3. Age- and gender-inappropriate care (where data allows).

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with flagged findings and a clinical risk score (0–100).
    """
    cutoff = datetime.utcnow().date() - timedelta(days=lookback_days)

    # --- 1. Duplicate incompatible procedures ---
    dup_rows = (
        db.query(
            Claim.beneficiary_id,
            Claim.claim_date,
            Claim.billing_code,
            func.count(Claim.id).label("occurrences"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .filter(Claim.billing_code.in_(INCOMPATIBLE_DUPLICATE_CODES))
        .filter(Claim.beneficiary_id.isnot(None))
        .group_by(Claim.beneficiary_id, Claim.claim_date, Claim.billing_code)
        .having(func.count(Claim.id) > 1)
        .all()
    )

    duplicate_procedures: List[Dict[str, Any]] = [
        {
            "beneficiary_id": str(r.beneficiary_id),
            "date": str(r.claim_date),
            "billing_code": r.billing_code,
            "occurrences": int(r.occurrences),
        }
        for r in dup_rows
    ]

    # --- 2. Excessive frequency ---
    frequency_result = detect_excessive_frequency(db, provider_id, lookback_days)

    # --- 3. Age-inappropriate care (pediatric codes for elderly) ---
    # We check for pediatric visit codes billed to beneficiaries also
    # receiving geriatric-level services (a proxy when DOB is unavailable).
    age_flags: List[Dict[str, Any]] = _detect_age_inappropriate(
        db, provider_id, cutoff,
    )

    # --- 4. Gender-inappropriate procedures ---
    gender_flags: List[Dict[str, Any]] = _detect_gender_inappropriate(
        db, provider_id, cutoff,
    )

    # Risk scoring
    risk = 0
    if duplicate_procedures:
        risk += min(40, len(duplicate_procedures) * 20)
    if frequency_result.get("flagged_beneficiaries"):
        risk += min(30, len(frequency_result["flagged_beneficiaries"]) * 5)
    if age_flags:
        risk += min(15, len(age_flags) * 5)
    if gender_flags:
        risk += min(15, len(gender_flags) * 5)
    risk = min(100, risk)

    return {
        "duplicate_incompatible_procedures": duplicate_procedures,
        "excessive_frequency": frequency_result,
        "age_inappropriate": age_flags,
        "gender_inappropriate": gender_flags,
        "clinical_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Temporal impossibility
# ---------------------------------------------------------------------------

def detect_temporal_impossibility(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect temporally impossible billing patterns.

    Checks:
    1. Billing for deceased beneficiaries (after status_date).
    2. Claims submitted before the service date.
    3. Services billed before provider registration (created_at).
    4. Provider billing more than 24 hours of services in a single day.

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with flagged findings and a temporal risk score (0–100).
    """
    deceased = detect_deceased_billing(db, provider_id)
    pre_submit = _detect_pre_submission(db, provider_id, lookback_days)
    pre_registration = _detect_pre_registration(db, provider_id)
    overwork = detect_25hour_days(db, provider_id, lookback_days)

    # Risk scoring
    risk = 0
    if deceased.get("claims_after_death"):
        risk += min(40, len(deceased["claims_after_death"]) * 10)
    if pre_submit.get("pre_submitted_claims"):
        risk += min(20, len(pre_submit["pre_submitted_claims"]) * 5)
    if pre_registration.get("pre_registration_claims", 0) > 0:
        risk += 15
    overwork_score = overwork.get("overwork_risk_score", 0)
    risk += int(overwork_score * 0.25)
    risk = min(100, risk)

    return {
        "deceased_billing": deceased,
        "pre_submission": pre_submit,
        "pre_registration": pre_registration,
        "overwork": overwork,
        "temporal_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Sub-detectors
# ---------------------------------------------------------------------------

def detect_25hour_days(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect days where a provider bills more than 24 hours of services.

    Uses ``Claim.units`` with a configurable hours-per-unit factor (default
    0.25 h = 15 min) to estimate total service hours per day.  Days
    exceeding 24 hours are physically impossible.

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with overwork days, statistics, and risk score.
    """
    cutoff = datetime.utcnow().date() - timedelta(days=lookback_days)

    rows = (
        db.query(
            Claim.claim_date,
            func.sum(Claim.units).label("total_units"),
            func.count(Claim.id).label("claim_count"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .group_by(Claim.claim_date)
        .order_by(Claim.claim_date)
        .all()
    )

    if not rows:
        return {
            "overwork_days": [],
            "overwork_day_count": 0,
            "max_hours_billed": 0.0,
            "avg_daily_hours": 0.0,
            "overwork_risk_score": 0,
        }

    overwork_days: List[Dict[str, Any]] = []
    daily_hours: List[float] = []

    for r in rows:
        units = int(r.total_units) if r.total_units else 0
        hours = units * DEFAULT_HOURS_PER_UNIT
        daily_hours.append(hours)

        if hours > 24.0:
            overwork_days.append({
                "date": str(r.claim_date),
                "total_units": units,
                "estimated_hours": round(hours, 2),
                "claim_count": int(r.claim_count),
            })

    hours_arr = np.array(daily_hours, dtype=float)
    max_hours = float(np.max(hours_arr)) if len(hours_arr) > 0 else 0.0
    avg_hours = float(np.mean(hours_arr)) if len(hours_arr) > 0 else 0.0

    # Risk scoring
    risk = 0
    if overwork_days:
        risk += min(60, len(overwork_days) * 10)
    if max_hours > 48:
        risk += 20
    elif max_hours > 36:
        risk += 10
    if avg_hours > 16:
        risk += 20
    elif avg_hours > 12:
        risk += 10
    risk = min(100, risk)

    return {
        "overwork_days": overwork_days[:20],
        "overwork_day_count": len(overwork_days),
        "max_hours_billed": round(max_hours, 2),
        "avg_daily_hours": round(avg_hours, 2),
        "overwork_risk_score": int(risk),
    }


def detect_deceased_billing(
    db: Session,
    provider_id: int,
) -> Dict[str, Any]:
    """Detect claims billed for deceased beneficiaries after their death date.

    Cross-references ``Beneficiary.status`` and ``Beneficiary.status_date``
    with claims from the given provider.

    Args:
        db: Database session.
        provider_id: Provider to analyze.

    Returns:
        Dictionary with post-death claims and risk score.
    """
    # Join claims to beneficiaries where status is 'deceased' and the
    # claim_date falls after the beneficiary's status_date (death date).
    rows = (
        db.query(
            Claim.beneficiary_id,
            Claim.claim_date,
            Claim.billing_code,
            Claim.amount,
            Beneficiary.status_date,
        )
        .join(Beneficiary, Claim.beneficiary_id == Beneficiary.id)
        .filter(Claim.provider_id == provider_id)
        .filter(Beneficiary.status == "deceased")
        .filter(Beneficiary.status_date.isnot(None))
        .filter(Claim.claim_date > Beneficiary.status_date)
        .order_by(Claim.claim_date)
        .all()
    )

    claims_after_death: List[Dict[str, Any]] = [
        {
            "beneficiary_id": str(r.beneficiary_id),
            "claim_date": str(r.claim_date),
            "billing_code": r.billing_code,
            "amount": float(r.amount),
            "death_date": str(r.status_date),
            "days_after_death": (
                _to_date(r.claim_date) - _to_date(r.status_date)
            ).days,
        }
        for r in rows
    ]

    total_amount = sum(c["amount"] for c in claims_after_death)

    risk = 0
    if claims_after_death:
        risk = min(100, len(claims_after_death) * 20)

    return {
        "claims_after_death": claims_after_death[:30],
        "total_post_death_claims": len(claims_after_death),
        "total_post_death_amount": round(total_amount, 2),
        "deceased_billing_risk_score": int(risk),
    }


def detect_excessive_frequency(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Detect beneficiaries receiving an excessive number of the same service.

    Compares per-beneficiary annual counts of specific billing codes
    against clinically reasonable thresholds (e.g., > 4 annual wellness
    visits per year is suspicious).

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with flagged beneficiaries and risk score.
    """
    cutoff = datetime.utcnow().date() - timedelta(days=lookback_days)

    if not EXCESSIVE_FREQUENCY_THRESHOLDS:
        return {"flagged_beneficiaries": [], "frequency_risk_score": 0}

    codes = list(EXCESSIVE_FREQUENCY_THRESHOLDS.keys())

    rows = (
        db.query(
            Claim.beneficiary_id,
            Claim.billing_code,
            func.count(Claim.id).label("visit_count"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .filter(Claim.billing_code.in_(codes))
        .filter(Claim.beneficiary_id.isnot(None))
        .group_by(Claim.beneficiary_id, Claim.billing_code)
        .all()
    )

    flagged: List[Dict[str, Any]] = []
    for r in rows:
        threshold = EXCESSIVE_FREQUENCY_THRESHOLDS.get(r.billing_code)
        if threshold is None:
            continue
        count = int(r.visit_count)
        if count > threshold:
            flagged.append({
                "beneficiary_id": str(r.beneficiary_id),
                "billing_code": r.billing_code,
                "visit_count": count,
                "threshold": threshold,
                "excess_ratio": round(count / threshold, 2),
            })

    flagged.sort(key=lambda x: x["excess_ratio"], reverse=True)

    risk = min(100, len(flagged) * 10)

    return {
        "flagged_beneficiaries": flagged[:30],
        "total_flagged": len(flagged),
        "frequency_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_age_inappropriate(
    db: Session,
    provider_id: int,
    cutoff: date,
) -> List[Dict[str, Any]]:
    """Flag pediatric billing codes used by providers whose other claims
    suggest an exclusively adult/geriatric patient population.

    Without beneficiary DOB in the schema we use a heuristic: if a
    provider has *no* claims outside of pediatric codes, these are
    likely legitimate.  We flag only when pediatric codes appear
    alongside predominantly non-pediatric billing.
    """
    # Count pediatric-code claims
    pediatric_rows = (
        db.query(
            Claim.beneficiary_id,
            Claim.claim_date,
            Claim.billing_code,
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .filter(Claim.beneficiary_id.isnot(None))
        .all()
    )

    if not pediatric_rows:
        return []

    ped_claims: List[Dict[str, Any]] = []
    non_ped_count = 0

    for r in pediatric_rows:
        is_ped = any(r.billing_code.startswith(p) for p in PEDIATRIC_CODE_PREFIXES)
        if is_ped:
            ped_claims.append({
                "beneficiary_id": str(r.beneficiary_id),
                "date": str(r.claim_date),
                "billing_code": r.billing_code,
            })
        else:
            non_ped_count += 1

    # Only flag if the provider is predominantly non-pediatric
    if non_ped_count == 0 or not ped_claims:
        return []

    ped_ratio = len(ped_claims) / (len(ped_claims) + non_ped_count)
    if ped_ratio > 0.5:
        # Provider is primarily pediatric — not suspicious
        return []

    return ped_claims[:20]


def _detect_gender_inappropriate(
    db: Session,
    provider_id: int,
    cutoff: date,
) -> List[Dict[str, Any]]:
    """Flag beneficiaries receiving both male-only and female-only procedures.

    Without explicit gender in the Beneficiary model we look for the same
    beneficiary receiving procedures from *both* gender-exclusive sets,
    which is clinically impossible.
    """
    all_gender_codes = MALE_ONLY_CODES | FEMALE_ONLY_CODES

    rows = (
        db.query(
            Claim.beneficiary_id,
            Claim.billing_code,
            Claim.claim_date,
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .filter(Claim.billing_code.in_(all_gender_codes))
        .filter(Claim.beneficiary_id.isnot(None))
        .all()
    )

    if not rows:
        return []

    # Group by beneficiary
    ben_codes: Dict[str, Dict[str, List[str]]] = {}
    for r in rows:
        bid = str(r.beneficiary_id)
        ben_codes.setdefault(bid, {"male": [], "female": []})
        if r.billing_code in MALE_ONLY_CODES:
            ben_codes[bid]["male"].append(r.billing_code)
        elif r.billing_code in FEMALE_ONLY_CODES:
            ben_codes[bid]["female"].append(r.billing_code)

    flags: List[Dict[str, Any]] = []
    for bid, codes in ben_codes.items():
        if codes["male"] and codes["female"]:
            flags.append({
                "beneficiary_id": bid,
                "male_codes": list(set(codes["male"])),
                "female_codes": list(set(codes["female"])),
            })

    return flags[:20]


def _detect_pre_submission(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """Find claims where ``submitted_date`` precedes ``claim_date``.

    A claim submitted *before* the service was allegedly rendered is
    temporally impossible and suggests fabricated billing.
    """
    cutoff = datetime.utcnow().date() - timedelta(days=lookback_days)

    rows = (
        db.query(
            Claim.claim_id,
            Claim.beneficiary_id,
            Claim.claim_date,
            Claim.submitted_date,
            Claim.billing_code,
            Claim.amount,
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff)
        .filter(Claim.submitted_date.isnot(None))
        .all()
    )

    pre_submitted: List[Dict[str, Any]] = []
    for r in rows:
        claim_dt = _to_date(r.claim_date)
        sub_dt = _to_date(r.submitted_date)
        if sub_dt < claim_dt:
            pre_submitted.append({
                "claim_id": str(r.claim_id) if r.claim_id else None,
                "beneficiary_id": str(r.beneficiary_id) if r.beneficiary_id else None,
                "claim_date": str(r.claim_date),
                "submitted_date": str(r.submitted_date),
                "billing_code": r.billing_code,
                "amount": float(r.amount),
                "days_before": (claim_dt - sub_dt).days,
            })

    return {
        "pre_submitted_claims": pre_submitted[:30],
        "total_pre_submitted": len(pre_submitted),
    }


def _detect_pre_registration(
    db: Session,
    provider_id: int,
) -> Dict[str, Any]:
    """Find claims with a service date before the provider's ``created_at``.

    Billing for services before a provider was registered is suspicious
    and may indicate backdated claims.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider or not provider.created_at:
        return {"pre_registration_claims": 0, "earliest_claim": None}

    reg_date = _to_date(provider.created_at)

    count = (
        db.query(func.count(Claim.id))
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date < reg_date)
        .scalar()
    )
    count = int(count) if count else 0

    earliest = None
    if count > 0:
        first = (
            db.query(func.min(Claim.claim_date))
            .filter(Claim.provider_id == provider_id)
            .filter(Claim.claim_date < reg_date)
            .scalar()
        )
        earliest = str(first) if first else None

    return {
        "pre_registration_claims": count,
        "provider_registered": str(reg_date),
        "earliest_claim": earliest,
    }


def _to_date(value: Any) -> date:
    """Coerce a date/datetime/string to a ``datetime.date``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # Handle common ISO formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return value  # type: ignore[return-value]


def _compute_impossibility_score(
    geospatial: Dict[str, Any],
    clinical: Dict[str, Any],
    temporal: Dict[str, Any],
) -> int:
    """Compute a weighted composite impossibility score (0–100).

    Weights:
        geospatial – 25%
        clinical   – 35%
        temporal   – 40%
    """
    g = geospatial.get("geospatial_risk_score", 0)
    c = clinical.get("clinical_risk_score", 0)
    t = temporal.get("temporal_risk_score", 0)

    composite = 0.25 * g + 0.35 * c + 0.40 * t
    return min(100, int(round(composite)))
