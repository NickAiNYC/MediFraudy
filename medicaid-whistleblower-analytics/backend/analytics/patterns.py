"""Known fraud pattern detection for Medicaid billing data."""

import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from models import Provider, Claim

logger = logging.getLogger(__name__)

# Billing codes commonly associated with elderly care fraud
ELDERLY_CARE_CODES = [
    "97110",  # Therapeutic exercises
    "97530",  # Therapeutic activities
    "97140",  # Manual therapy
    "99213",  # Office visit, established patient
    "99214",  # Office visit, established patient (higher complexity)
    "T1019",  # Personal care services
    "T1020",  # Personal care services (per diem)
    "S5150",  # Unskilled respite care
    "T2003",  # Non-emergency transportation
]

# Target codes from recent Brooklyn/Queens/Albany prosecutions
TARGET_CODES = {
    "adult_day_care": ["T2024", "T2025", "S5100", "S5101", "S5102", "S5105"],
    "home_health": [
        "G0151", "G0152", "G0153", "G0154",
        "G0155", "G0156", "G0157", "G0159",
    ],
    "pharmacy_kickback_indicators": ["J-code range"],
    "capacity_related": ["T2024", "T2025"],
}


def detect_fraud_patterns(
    db: Session, provider_id: Optional[int] = None
) -> list[dict]:
    """Run a suite of fraud pattern checks.

    Args:
        db: Database session.
        provider_id: Optional provider to focus on. If None, scans all.

    Returns:
        List of detected patterns with details.
    """
    results: list[dict] = []
    results.extend(_high_volume_billing(db, provider_id))
    results.extend(_unusual_code_combinations(db, provider_id))
    results.extend(_weekend_holiday_billing(db, provider_id))
    return results


def _high_volume_billing(
    db: Session, provider_id: Optional[int] = None
) -> list[dict]:
    """Detect sustained high-volume billing relative to peers.

    A provider is flagged if their monthly claim count exceeds
    twice the peer-group average for three or more months.
    """
    query = (
        db.query(
            Provider.id,
            Provider.name,
            extract("year", Claim.claim_date).label("year"),
            extract("month", Claim.claim_date).label("month"),
            func.count(Claim.id).label("claim_count"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .group_by(Provider.id, "year", "month")
    )
    if provider_id:
        query = query.filter(Provider.id == provider_id)

    rows = query.all()
    if not rows:
        return []

    # Compute overall monthly average
    totals = [int(r.claim_count) for r in rows]
    avg = sum(totals) / len(totals) if totals else 0

    flagged: dict[int, list] = {}
    for r in rows:
        if int(r.claim_count) > avg * 2:
            flagged.setdefault(r.id, []).append({
                "year": int(r.year),
                "month": int(r.month),
                "count": int(r.claim_count),
            })

    results = []
    for pid, months in flagged.items():
        if len(months) >= 3:
            name = next((r.name for r in rows if r.id == pid), "Unknown")
            results.append({
                "pattern": "sustained_high_volume",
                "provider_id": pid,
                "provider_name": name,
                "months_flagged": len(months),
                "details": months,
            })
    return results


def _unusual_code_combinations(
    db: Session, provider_id: Optional[int] = None
) -> list[dict]:
    """Detect providers billing unusual combinations of codes.

    Flags providers who bill across many distinct categories,
    which may indicate upcoding or unbundling.
    """
    query = (
        db.query(
            Provider.id,
            Provider.name,
            func.count(func.distinct(Claim.billing_code)).label("unique_codes"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .group_by(Provider.id)
    )
    if provider_id:
        query = query.filter(Provider.id == provider_id)

    rows = query.all()
    if not rows:
        return []

    counts = [int(r.unique_codes) for r in rows]
    avg = sum(counts) / len(counts) if counts else 0

    results = []
    for r in rows:
        if int(r.unique_codes) > avg * 2:
            results.append({
                "pattern": "unusual_code_combinations",
                "provider_id": r.id,
                "provider_name": r.name,
                "unique_codes": int(r.unique_codes),
                "peer_average": round(avg, 1),
            })
    return results


def _weekend_holiday_billing(
    db: Session, provider_id: Optional[int] = None
) -> list[dict]:
    """Detect providers with disproportionate weekend billing.

    Flags providers where more than 30 % of claims fall on
    Saturday or Sunday (day-of-week 0 = Monday in some DBs).
    """
    total_q = (
        db.query(
            Provider.id,
            Provider.name,
            func.count(Claim.id).label("total"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .group_by(Provider.id)
    )
    if provider_id:
        total_q = total_q.filter(Provider.id == provider_id)

    weekend_q = (
        db.query(
            Provider.id,
            func.count(Claim.id).label("weekend_count"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(extract("dow", Claim.claim_date).in_([0, 6]))
        .group_by(Provider.id)
    )
    if provider_id:
        weekend_q = weekend_q.filter(Provider.id == provider_id)

    totals = {r.id: (r.name, int(r.total)) for r in total_q.all()}
    weekends = {r.id: int(r.weekend_count) for r in weekend_q.all()}

    results = []
    for pid, (name, total) in totals.items():
        wknd = weekends.get(pid, 0)
        ratio = wknd / total if total else 0
        if ratio > 0.30:
            results.append({
                "pattern": "weekend_holiday_anomaly",
                "provider_id": pid,
                "provider_name": name,
                "weekend_claims": wknd,
                "total_claims": total,
                "weekend_ratio": round(ratio, 3),
            })
    return results
