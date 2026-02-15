"""Temporal Intelligence Engine for Medicaid fraud detection.

Detects time-based fraud patterns that evade point-in-time statistical analysis:
- Billing velocity changes (calm → spike → calm fraud cycles)
- Seasonal anomalies (claims that deviate from expected seasonal norms)
- Event correlation (billing spikes after regulatory or policy changes)
- Claim lifecycle analysis (submission → payment timeline irregularities)
- Statute of limitations tracking (6-year FCA lookback window)

Uses CUSUM (cumulative sum control chart) for change point detection
rather than external libraries, ensuring portability across environments.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from sqlalchemy import func, extract, and_
from sqlalchemy.orm import Session

from models import Provider, Claim

logger = logging.getLogger(__name__)

# FCA statute of limitations: 6 years from violation, or 3 years from
# discovery (max 10 years from violation). We use the 6-year default.
FCA_LOOKBACK_YEARS = 6

# Seasonal month groupings for norm calculation
SEASONS = {
    "winter": [12, 1, 2],
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "fall": [9, 10, 11],
}

# US federal holidays (month, day) — static holidays only
FEDERAL_HOLIDAYS = [
    (1, 1),    # New Year's Day
    (7, 4),    # Independence Day
    (12, 25),  # Christmas Day
]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyze_temporal_patterns(
    db: Session,
    provider_id: int,
    lookback_days: int = 730,
) -> Dict[str, Any]:
    """Run full temporal intelligence analysis for a provider.

    Combines velocity change detection, seasonal anomaly detection,
    weekend/holiday ghost-claim analysis, claim lifecycle analysis,
    and statute of limitations tracking into a single report.

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Number of days to look back (default 2 years).

    Returns:
        Dictionary with all temporal analysis results and an overall
        temporal risk score (0–100).
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        logger.warning("Provider %d not found", provider_id)
        return {"error": "Provider not found", "temporal_risk_score": 0}

    velocity = detect_velocity_changes(db, provider_id, lookback_days)
    seasonal = detect_seasonal_anomalies(db, provider_id, lookback_days)
    weekend_holiday = detect_weekend_holiday_anomalies(db, provider_id, lookback_days)
    lifecycle = analyze_claim_lifecycle(db, provider_id, lookback_days)
    statute = track_statute_of_limitations(db, provider_id)

    # Composite risk score (0–100)
    score = _compute_temporal_risk_score(
        velocity, seasonal, weekend_holiday, lifecycle,
    )

    logger.info(
        "Temporal analysis for provider %d: score=%d", provider_id, score,
    )

    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "lookback_days": lookback_days,
        "temporal_risk_score": score,
        "velocity_analysis": velocity,
        "seasonal_analysis": seasonal,
        "weekend_holiday_analysis": weekend_holiday,
        "lifecycle_analysis": lifecycle,
        "statute_of_limitations": statute,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Velocity change detection
# ---------------------------------------------------------------------------

def detect_velocity_changes(
    db: Session,
    provider_id: int,
    lookback_days: int = 730,
) -> Dict[str, Any]:
    """Detect billing rate changes over time.

    Aggregates claims into weekly buckets then applies CUSUM change-point
    detection to find sudden shifts in billing volume or amount.  The
    classic fraud pattern is calm → spike → calm, where the spike is an
    intentional burst of fraudulent billing sandwiched between normal
    behavior.

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with weekly time-series, detected change points,
        spike periods, and a velocity risk score (0–100).
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    rows = (
        db.query(
            Claim.claim_date,
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff.date())
        .group_by(Claim.claim_date)
        .order_by(Claim.claim_date)
        .all()
    )

    if not rows:
        return {
            "weekly_series": [],
            "change_points": [],
            "spike_periods": [],
            "velocity_risk_score": 0,
        }

    # Build a pandas Series indexed by date, resample to weekly
    dates = [r.claim_date for r in rows]
    counts = [int(r.claim_count) for r in rows]
    amounts = [float(r.total_amount) for r in rows]

    df = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "count": counts,
        "amount": amounts,
    }).set_index("date")

    weekly = df.resample("W").sum().fillna(0)

    if weekly.empty or len(weekly) < 4:
        return {
            "weekly_series": [],
            "change_points": [],
            "spike_periods": [],
            "velocity_risk_score": 0,
        }

    count_values = weekly["count"].values.astype(float)
    amount_values = weekly["amount"].values.astype(float)

    # Detect change points on claim counts
    count_cps = detect_change_points(count_values, threshold=2.0)
    amount_cps = detect_change_points(amount_values, threshold=2.0)

    # Identify spike periods (calm → spike → calm)
    spike_periods = _identify_spike_periods(count_values, weekly.index, count_cps)

    # Build serializable weekly series
    weekly_series = [
        {
            "week_start": str(idx.date()),
            "claim_count": int(c),
            "total_amount": float(a),
        }
        for idx, c, a in zip(weekly.index, count_values, amount_values)
    ]

    # Risk score: more change points and spike periods → higher risk
    risk = min(100, len(count_cps) * 15 + len(spike_periods) * 25)

    return {
        "weekly_series": weekly_series,
        "change_points": count_cps + amount_cps,
        "spike_periods": spike_periods,
        "velocity_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Seasonal anomaly detection
# ---------------------------------------------------------------------------

def detect_seasonal_anomalies(
    db: Session,
    provider_id: int,
    lookback_days: int = 730,
) -> Dict[str, Any]:
    """Find months where provider billing deviates from seasonal norms.

    Computes monthly claim volume and amount, derives seasonal baselines
    (mean/std per calendar month), then flags months that exceed ±2σ.

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with monthly norms, anomalous months, and risk score.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    rows = (
        db.query(
            extract("year", Claim.claim_date).label("year"),
            extract("month", Claim.claim_date).label("month"),
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff.date())
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    if not rows:
        return {
            "monthly_data": [],
            "seasonal_norms": {},
            "anomalous_months": [],
            "seasonal_risk_score": 0,
        }

    # Organize data by month number across years
    monthly_map: Dict[int, List[float]] = {m: [] for m in range(1, 13)}
    monthly_data = []

    for r in rows:
        month = int(r.month)
        year = int(r.year)
        count = int(r.claim_count)
        amount = float(r.total_amount)
        monthly_map[month].append(count)
        monthly_data.append({
            "year": year,
            "month": month,
            "claim_count": count,
            "total_amount": amount,
        })

    # Seasonal norms: mean & std per calendar month
    seasonal_norms: Dict[str, Any] = {}
    for month, values in monthly_map.items():
        if values:
            arr = np.array(values, dtype=float)
            seasonal_norms[str(month)] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "n": len(values),
            }

    # Flag anomalous months
    anomalous: List[Dict[str, Any]] = []
    for entry in monthly_data:
        norm = seasonal_norms.get(str(entry["month"]))
        if not norm or norm["std"] == 0 or norm["n"] < 2:
            continue
        z = (entry["claim_count"] - norm["mean"]) / norm["std"]
        if abs(z) >= 2.0:
            anomalous.append({
                "year": entry["year"],
                "month": entry["month"],
                "claim_count": entry["claim_count"],
                "z_score": round(float(z), 2),
                "direction": "above" if z > 0 else "below",
            })

    risk = min(100, len(anomalous) * 20)

    return {
        "monthly_data": monthly_data,
        "seasonal_norms": seasonal_norms,
        "anomalous_months": anomalous,
        "seasonal_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Weekend / holiday anomaly detection
# ---------------------------------------------------------------------------

def detect_weekend_holiday_anomalies(
    db: Session,
    provider_id: int,
    lookback_days: int = 730,
) -> Dict[str, Any]:
    """Detect ghost claims filed on weekends or federal holidays.

    Many facilities are closed on weekends and holidays.  Claims on
    those days—especially at high volume—are strong fraud indicators
    (Brooklyn $68M case pattern).

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with weekend/holiday claim counts and risk score.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    rows = (
        db.query(Claim.claim_date, func.count(Claim.id).label("cnt"))
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff.date())
        .group_by(Claim.claim_date)
        .all()
    )

    if not rows:
        return {
            "total_days": 0,
            "weekend_claims": 0,
            "holiday_claims": 0,
            "weekend_pct": 0.0,
            "holiday_pct": 0.0,
            "weekend_holiday_risk_score": 0,
        }

    total_claims = 0
    weekend_claims = 0
    holiday_claims = 0
    weekend_dates: List[str] = []
    holiday_dates: List[str] = []

    for r in rows:
        claim_dt = r.claim_date
        if isinstance(claim_dt, datetime):
            claim_dt = claim_dt.date()
        cnt = int(r.cnt)
        total_claims += cnt

        # Weekend check (Saturday=5, Sunday=6 in Python weekday())
        if claim_dt.weekday() >= 5:
            weekend_claims += cnt
            weekend_dates.append(str(claim_dt))

        # Holiday check
        if (claim_dt.month, claim_dt.day) in FEDERAL_HOLIDAYS:
            holiday_claims += cnt
            holiday_dates.append(str(claim_dt))

    weekend_pct = (weekend_claims / total_claims * 100) if total_claims else 0.0
    holiday_pct = (holiday_claims / total_claims * 100) if total_claims else 0.0

    # Risk: >20% weekend claims is highly suspicious
    risk = 0
    if weekend_pct > 25:
        risk += 60
    elif weekend_pct > 15:
        risk += 35
    elif weekend_pct > 5:
        risk += 15

    if holiday_claims > 0:
        risk += min(40, holiday_claims * 10)

    risk = min(100, risk)

    return {
        "total_claims": total_claims,
        "weekend_claims": weekend_claims,
        "holiday_claims": holiday_claims,
        "weekend_pct": round(float(weekend_pct), 2),
        "holiday_pct": round(float(holiday_pct), 2),
        "weekend_dates_sample": weekend_dates[:20],
        "holiday_dates_sample": holiday_dates[:20],
        "weekend_holiday_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Claim lifecycle analysis
# ---------------------------------------------------------------------------

def analyze_claim_lifecycle(
    db: Session,
    provider_id: int,
    lookback_days: int = 730,
) -> Dict[str, Any]:
    """Analyze submission-to-service lag and billing patterns.

    Fraudulent providers often submit claims in large batches long after
    the purported service date, or submit with suspiciously uniform lag
    times (robotic billing).

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with lifecycle statistics and risk score.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    rows = (
        db.query(Claim.claim_date, Claim.submitted_date, Claim.amount)
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff.date())
        .filter(Claim.submitted_date.isnot(None))
        .all()
    )

    if not rows:
        return {
            "total_with_dates": 0,
            "avg_lag_days": None,
            "median_lag_days": None,
            "max_lag_days": None,
            "lag_std_days": None,
            "suspicious_batches": [],
            "lifecycle_risk_score": 0,
        }

    lags: List[float] = []
    submission_dates: List[datetime] = []

    for r in rows:
        claim_dt = r.claim_date
        sub_dt = r.submitted_date
        if isinstance(claim_dt, date) and not isinstance(claim_dt, datetime):
            claim_dt = datetime.combine(claim_dt, datetime.min.time())
        if isinstance(sub_dt, date) and not isinstance(sub_dt, datetime):
            sub_dt = datetime.combine(sub_dt, datetime.min.time())
        lag = (sub_dt - claim_dt).total_seconds() / 86400.0
        lags.append(lag)
        submission_dates.append(sub_dt)

    lag_arr = np.array(lags, dtype=float)
    avg_lag = float(np.mean(lag_arr))
    median_lag = float(np.median(lag_arr))
    max_lag = float(np.max(lag_arr))
    lag_std = float(np.std(lag_arr))

    # Detect batch submissions: many claims submitted on the same date
    sub_counts: Dict[str, int] = {}
    for dt in submission_dates:
        key = str(dt.date())
        sub_counts[key] = sub_counts.get(key, 0) + 1

    total_with_dates = len(rows)
    batch_threshold = max(10, total_with_dates * 0.1)
    suspicious_batches = [
        {"date": d, "count": c}
        for d, c in sorted(sub_counts.items(), key=lambda x: x[1], reverse=True)
        if c >= batch_threshold
    ]

    # Risk scoring
    risk = 0
    if avg_lag > 90:
        risk += 30
    elif avg_lag > 30:
        risk += 15

    # Very low std in lag suggests automated/robotic billing
    if lag_std < 1.0 and total_with_dates > 20:
        risk += 25

    if suspicious_batches:
        risk += min(45, len(suspicious_batches) * 15)

    risk = min(100, risk)

    return {
        "total_with_dates": total_with_dates,
        "avg_lag_days": round(avg_lag, 1),
        "median_lag_days": round(median_lag, 1),
        "max_lag_days": round(max_lag, 1),
        "lag_std_days": round(lag_std, 2),
        "suspicious_batches": suspicious_batches[:10],
        "lifecycle_risk_score": int(risk),
    }


# ---------------------------------------------------------------------------
# Statute of limitations tracking
# ---------------------------------------------------------------------------

def track_statute_of_limitations(
    db: Session,
    provider_id: int,
) -> Dict[str, Any]:
    """Track the 6-year False Claims Act lookback window.

    Identifies the provider's earliest and latest claim dates, determines
    which claims fall within the FCA 6-year statute of limitations, and
    estimates the total exposure amount within that window.

    Args:
        db: Database session.
        provider_id: Provider to analyze.

    Returns:
        Dictionary with statute tracking details.
    """
    fca_cutoff = datetime.utcnow().date() - timedelta(days=365 * FCA_LOOKBACK_YEARS)

    # Overall date range
    date_range = (
        db.query(
            func.min(Claim.claim_date).label("earliest"),
            func.max(Claim.claim_date).label("latest"),
            func.count(Claim.id).label("total_claims"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .filter(Claim.provider_id == provider_id)
        .first()
    )

    if not date_range or date_range.total_claims == 0:
        return {
            "fca_lookback_years": FCA_LOOKBACK_YEARS,
            "fca_cutoff_date": str(fca_cutoff),
            "total_claims": 0,
            "claims_in_window": 0,
            "amount_in_window": 0.0,
            "claims_expired": 0,
            "amount_expired": 0.0,
            "earliest_claim": None,
            "latest_claim": None,
            "years_of_data": 0,
        }

    # Claims within FCA window
    in_window = (
        db.query(
            func.count(Claim.id).label("cnt"),
            func.sum(Claim.amount).label("amt"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= fca_cutoff)
        .first()
    )

    total_claims = int(date_range.total_claims)
    total_amount = float(date_range.total_amount) if date_range.total_amount else 0.0
    claims_in_window = int(in_window.cnt) if in_window and in_window.cnt else 0
    amount_in_window = float(in_window.amt) if in_window and in_window.amt else 0.0

    earliest = date_range.earliest
    latest = date_range.latest
    if isinstance(earliest, datetime):
        earliest = earliest.date()
    if isinstance(latest, datetime):
        latest = latest.date()

    years_of_data = 0.0
    if earliest and latest:
        years_of_data = (latest - earliest).days / 365.25

    # Urgency: claims approaching the 6-year deadline
    approaching_expiry = 0
    if earliest and earliest < fca_cutoff:
        expiring_soon = fca_cutoff + timedelta(days=180)
        expiring = (
            db.query(func.count(Claim.id))
            .filter(Claim.provider_id == provider_id)
            .filter(Claim.claim_date >= fca_cutoff)
            .filter(Claim.claim_date <= expiring_soon)
            .scalar()
        )
        approaching_expiry = int(expiring) if expiring else 0

    return {
        "fca_lookback_years": FCA_LOOKBACK_YEARS,
        "fca_cutoff_date": str(fca_cutoff),
        "earliest_claim": str(earliest) if earliest else None,
        "latest_claim": str(latest) if latest else None,
        "years_of_data": round(float(years_of_data), 1),
        "total_claims": total_claims,
        "total_amount": round(total_amount, 2),
        "claims_in_window": claims_in_window,
        "amount_in_window": round(amount_in_window, 2),
        "claims_expired": total_claims - claims_in_window,
        "amount_expired": round(total_amount - amount_in_window, 2),
        "claims_approaching_expiry_180d": approaching_expiry,
    }


# ---------------------------------------------------------------------------
# Billing baseline calculation
# ---------------------------------------------------------------------------

def calculate_billing_baseline(
    db: Session,
    provider_id: int,
    lookback_days: int = 730,
) -> Dict[str, Any]:
    """Calculate baseline billing behaviour for a provider.

    Produces weekly mean/std claim count and amount, which serve as the
    reference for velocity and seasonal anomaly detection.

    Args:
        db: Database session.
        provider_id: Provider to analyze.
        lookback_days: Days to look back.

    Returns:
        Dictionary with baseline statistics.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    rows = (
        db.query(
            Claim.claim_date,
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .filter(Claim.provider_id == provider_id)
        .filter(Claim.claim_date >= cutoff.date())
        .group_by(Claim.claim_date)
        .order_by(Claim.claim_date)
        .all()
    )

    if not rows:
        return {
            "weekly_mean_count": None,
            "weekly_std_count": None,
            "weekly_mean_amount": None,
            "weekly_std_amount": None,
            "total_weeks": 0,
        }

    dates = [r.claim_date for r in rows]
    counts = [int(r.claim_count) for r in rows]
    amounts = [float(r.total_amount) for r in rows]

    df = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "count": counts,
        "amount": amounts,
    }).set_index("date")

    weekly = df.resample("W").sum().fillna(0)

    if weekly.empty:
        return {
            "weekly_mean_count": None,
            "weekly_std_count": None,
            "weekly_mean_amount": None,
            "weekly_std_amount": None,
            "total_weeks": 0,
        }

    count_arr = weekly["count"].values.astype(float)
    amount_arr = weekly["amount"].values.astype(float)

    return {
        "weekly_mean_count": round(float(np.mean(count_arr)), 2),
        "weekly_std_count": round(float(np.std(count_arr)), 2),
        "weekly_mean_amount": round(float(np.mean(amount_arr)), 2),
        "weekly_std_amount": round(float(np.std(amount_arr)), 2),
        "total_weeks": int(len(weekly)),
    }


# ---------------------------------------------------------------------------
# CUSUM change-point detection
# ---------------------------------------------------------------------------

def detect_change_points(
    values: List[float],
    threshold: float = 2.0,
) -> List[Dict[str, Any]]:
    """Detect change points in a time series using CUSUM.

    Implements a two-sided CUSUM (cumulative sum control chart) algorithm.
    A change point is flagged when the cumulative deviation from the mean
    exceeds ``threshold`` standard deviations.

    Args:
        values: Sequence of numeric observations (e.g. weekly claim counts).
        threshold: Number of standard deviations for the CUSUM decision
            boundary.  Lower values increase sensitivity.

    Returns:
        List of dictionaries, one per detected change point, each with
        ``index``, ``direction`` ("increase" | "decrease"), and
        ``magnitude`` (CUSUM value at detection, in units of σ).
    """
    arr = np.array(values, dtype=float)
    n = len(arr)

    if n < 4:
        return []

    mean = float(np.mean(arr))
    std = float(np.std(arr))

    if std == 0:
        return []

    # Normalize to z-scores
    z = (arr - mean) / std

    # Allowable slack (k) — half the shift we want to detect
    k = 0.5

    # Two-sided CUSUM accumulators
    s_pos = np.zeros(n)
    s_neg = np.zeros(n)
    change_points: List[Dict] = []

    for i in range(1, n):
        s_pos[i] = max(0.0, s_pos[i - 1] + z[i] - k)
        s_neg[i] = max(0.0, s_neg[i - 1] - z[i] - k)

        if s_pos[i] > threshold:
            change_points.append({
                "index": int(i),
                "direction": "increase",
                "magnitude": round(float(s_pos[i]), 2),
            })
            # Reset after detection to find subsequent shifts
            s_pos[i] = 0.0

        if s_neg[i] > threshold:
            change_points.append({
                "index": int(i),
                "direction": "decrease",
                "magnitude": round(float(s_neg[i]), 2),
            })
            s_neg[i] = 0.0

    return change_points


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _identify_spike_periods(
    values: np.ndarray,
    index: pd.DatetimeIndex,
    change_points: List[Dict],
) -> List[Dict[str, Any]]:
    """Identify calm → spike → calm periods from change-point list.

    Pairs an "increase" change point with the next "decrease" change
    point to define a spike window. Only spikes where the mean value
    within the window exceeds 2× the overall mean are retained.
    """
    spikes: List[Dict[str, Any]] = []
    overall_mean = float(np.mean(values)) if len(values) > 0 else 0.0

    increases = [cp for cp in change_points if cp["direction"] == "increase"]
    decreases = [cp for cp in change_points if cp["direction"] == "decrease"]

    for inc in increases:
        # Find the next decrease after this increase
        matching = [d for d in decreases if d["index"] > inc["index"]]
        if matching:
            dec = matching[0]
            start_idx = inc["index"]
            end_idx = dec["index"]
        else:
            # Spike continues to end of series
            start_idx = inc["index"]
            end_idx = len(values) - 1

        spike_values = values[start_idx:end_idx + 1]
        if len(spike_values) == 0:
            continue

        spike_mean = float(np.mean(spike_values))
        if overall_mean > 0 and spike_mean >= 2.0 * overall_mean:
            spikes.append({
                "start_index": int(start_idx),
                "end_index": int(end_idx),
                "start_date": str(index[start_idx].date()) if start_idx < len(index) else None,
                "end_date": str(index[end_idx].date()) if end_idx < len(index) else None,
                "duration_weeks": int(end_idx - start_idx + 1),
                "spike_mean": round(spike_mean, 2),
                "overall_mean": round(overall_mean, 2),
                "spike_ratio": round(spike_mean / overall_mean, 2),
            })

    return spikes


def _compute_temporal_risk_score(
    velocity: Dict[str, Any],
    seasonal: Dict[str, Any],
    weekend_holiday: Dict[str, Any],
    lifecycle: Dict[str, Any],
) -> int:
    """Compute a weighted composite temporal risk score (0–100).

    Weights:
        velocity      – 30%
        seasonal      – 20%
        weekend/hol   – 30%
        lifecycle     – 20%
    """
    v = velocity.get("velocity_risk_score", 0)
    s = seasonal.get("seasonal_risk_score", 0)
    w = weekend_holiday.get("weekend_holiday_risk_score", 0)
    lc = lifecycle.get("lifecycle_risk_score", 0)

    composite = 0.30 * v + 0.20 * s + 0.30 * w + 0.20 * lc
    return min(100, int(round(composite)))
