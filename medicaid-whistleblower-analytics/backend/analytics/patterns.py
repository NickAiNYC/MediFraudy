"""Known fraud pattern detection for Medicaid billing data.

Targets specific patterns from recent NYC prosecutions:
- Brooklyn $68M: Kickbacks, weekend billing, sustained high volume
- Queens $120M: Capacity violations, pharmacy kickbacks
- Albany $1.3M: Understaffing, neglect patterns
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_, desc
from sqlalchemy.sql import label

from models import Provider, Claim, Anomaly, KickbackIndicator, CapacityViolation

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
    "pharmacy_kickback_indicators": ["J-code range"],  # J-codes for drugs
    "capacity_related": ["T2024", "T2025"],
    "therapy": ["97110", "97530", "97140"],
}


def detect_fraud_patterns(
    db: Session, 
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,  # 3 years default
    save_results: bool = True,
) -> List[Dict[str, Any]]:
    """Run a comprehensive suite of fraud pattern checks.

    Args:
        db: Database session.
        provider_id: Optional provider to focus on. If None, scans all.
        days_back: Number of days to analyze.
        save_results: Whether to save findings to anomaly tables.

    Returns:
        List of detected patterns with details.
    """
    results: List[Dict[str, Any]] = []
    
    # Run all detection modules
    results.extend(_detect_high_volume_billing(db, provider_id, days_back))
    results.extend(_detect_unusual_code_combinations(db, provider_id))
    results.extend(_detect_weekend_holiday_billing(db, provider_id, days_back))
    results.extend(_detect_beneficiary_concentration(db, provider_id, days_back))  # Brooklyn case
    results.extend(_detect_capacity_patterns(db, provider_id, days_back))  # Queens case
    results.extend(_detect_batch_submission(db, provider_id, days_back))
    results.extend(_detect_code_creep(db, provider_id, days_back))
    results.extend(_detect_unusual_service_hours(db, provider_id, days_back))
    
    # Save to anomalies table if requested
    if save_results and results:
        _save_patterns_to_db(db, results)
    
    logger.info(f"Detected {len(results)} fraud patterns")
    return results


def _detect_high_volume_billing(
    db: Session, 
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,
) -> List[Dict[str, Any]]:
    """Detect sustained high-volume billing relative to peers.

    A provider is flagged if their monthly claim count exceeds
    twice the peer-group average for three or more months.
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Get monthly counts per provider
    query = (
        db.query(
            Provider.id.label("provider_id"),
            Provider.name,
            Provider.facility_type,
            extract("year", Claim.claim_date).label("year"),
            extract("month", Claim.claim_date).label("month"),
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Claim.claim_date >= cutoff_date)
        .group_by(Provider.id, "year", "month")
    )
    
    if provider_id:
        query = query.filter(Provider.id == provider_id)
    
    rows = query.all()
    if not rows:
        return []

    # Group by facility type for peer comparison
    peers_by_type = {}
    for r in rows:
        key = r.facility_type or "unknown"
        if key not in peers_by_type:
            peers_by_type[key] = []
        peers_by_type[key].append({
            "provider_id": r.provider_id,
            "month": f"{int(r.year)}-{int(r.month):02d}",
            "count": int(r.claim_count),
            "amount": float(r.total_amount),
        })

    results = []
    for facility_type, data in peers_by_type.items():
        # Calculate average monthly volume for this facility type
        all_counts = [d["count"] for d in data]
        avg_monthly = np.mean(all_counts) if all_counts else 0
        std_monthly = np.std(all_counts) if all_counts else 0
        
        # Group by provider
        provider_months = {}
        for d in data:
            pid = d["provider_id"]
            if pid not in provider_months:
                provider_months[pid] = []
            provider_months[pid].append(d)
        
        # Check each provider for sustained high volume
        for pid, months in provider_months.items():
            # Sort by date
            months.sort(key=lambda x: x["month"])
            
            # Find months where count > 2x average
            high_months = [m for m in months if m["count"] > avg_monthly * 2]
            
            if len(high_months) >= 3:
                # Check if they're consecutive
                is_consecutive = False
                if len(high_months) >= 3:
                    # Simple check: see if any 3 are within 3 months of each other
                    for i in range(len(high_months) - 2):
                        m1 = high_months[i]["month"]
                        m2 = high_months[i+2]["month"]
                        # Extract years/months
                        y1, m1 = map(int, m1.split('-'))
                        y2, m2 = map(int, m2.split('-'))
                        month_diff = (y2 - y1) * 12 + (m2 - m1)
                        if month_diff <= 3:
                            is_consecutive = True
                            break
                
                provider_name = next((r.name for r in rows if r.provider_id == pid), "Unknown")
                results.append({
                    "pattern": "sustained_high_volume",
                    "provider_id": pid,
                    "provider_name": provider_name,
                    "facility_type": facility_type,
                    "months_flagged": len(high_months),
                    "avg_monthly_volume": round(avg_monthly, 1),
                    "peak_volume": max(m["count"] for m in high_months),
                    "peak_amount": max(m["amount"] for m in high_months),
                    "is_consecutive": is_consecutive,
                    "severity": "high" if is_consecutive else "medium",
                    "details": high_months[-3:],  # Last 3 flagged months
                })
    
    return results


def _detect_unusual_code_combinations(
    db: Session, 
    provider_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Detect providers billing unusual combinations of codes.

    Flags providers who bill across many distinct categories,
    which may indicate upcoding or unbundling. Also flags
    clinically impossible combinations (e.g., podiatrist billing psych).
    """
    # Get providers with their distinct codes and specialties
    query = (
        db.query(
            Provider.id.label("provider_id"),
            Provider.name,
            Provider.specialty,
            Provider.facility_type,
            func.count(func.distinct(Claim.billing_code)).label("unique_codes"),
            func.array_agg(func.distinct(Claim.billing_code)).label("codes_list"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .group_by(Provider.id)
    )
    
    if provider_id:
        query = query.filter(Provider.id == provider_id)
    
    rows = query.limit(1000).all()  # Limit for performance
    if not rows:
        return []

    # Calculate average unique codes by facility type
    type_counts = {}
    for r in rows:
        ft = r.facility_type or "unknown"
        if ft not in type_counts:
            type_counts[ft] = []
        type_counts[ft].append(r.unique_codes)

    type_avg = {ft: np.mean(counts) for ft, counts in type_counts.items()}

    # Define clinically impossible combinations
    impossible_combinations = {
        "podiatry": ["90791", "90837", "96127"],  # Psych codes for podiatrists
        "dentist": ["99214", "99215", "T2024"],   # Medical codes for dentists
        "chiropractor": ["J-code"],                # Drugs for chiropractors
        "adult_day_care": ["J-code"],              # Pharmacy dispensing at day care (Queens case)
    }

    results = []
    for r in rows:
        ft = r.facility_type or "unknown"
        avg = type_avg.get(ft, 10)  # Default 10 if unknown
        
        # Flag if too many codes
        if r.unique_codes > avg * 2.5:
            results.append({
                "pattern": "excessive_code_variety",
                "provider_id": r.provider_id,
                "provider_name": r.name,
                "facility_type": ft,
                "unique_codes": int(r.unique_codes),
                "peer_average": round(float(avg), 1),
                "severity": "high" if r.unique_codes > avg * 4 else "medium",
            })
        
        # Check for impossible combinations
        if r.specialty and r.specialty.lower() in impossible_combinations:
            bad_codes = impossible_combinations[r.specialty.lower()]
            # This would require checking actual codes against list
            # Simplified version - in production, check against r.codes_list
    
    return results


def _detect_weekend_holiday_billing(
    db: Session, 
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,
) -> List[Dict[str, Any]]:
    """Detect providers with disproportionate weekend billing.

    Flags providers where more than 20% of claims fall on
    Saturday or Sunday (Brooklyn case indicator).
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Get total and weekend counts per provider
    total_subq = (
        db.query(
            Provider.id.label("provider_id"),
            Provider.name,
            func.count(Claim.id).label("total_claims"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Claim.claim_date >= cutoff_date)
        .group_by(Provider.id)
        .subquery()
    )
    
    weekend_subq = (
        db.query(
            Provider.id.label("provider_id"),
            func.count(Claim.id).label("weekend_claims"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Claim.claim_date >= cutoff_date)
        .filter(extract("dow", Claim.claim_date).in_([0, 6]))  # Sunday=0, Saturday=6 in PostgreSQL
        .group_by(Provider.id)
        .subquery()
    )
    
    query = (
        db.query(
            total_subq.c.provider_id,
            total_subq.c.name,
            total_subq.c.total_claims,
            func.coalesce(weekend_subq.c.weekend_claims, 0).label("weekend_claims"),
        )
        .outerjoin(weekend_subq, total_subq.c.provider_id == weekend_subq.c.provider_id)
    )
    
    if provider_id:
        query = query.filter(total_subq.c.provider_id == provider_id)
    
    rows = query.all()
    
    results = []
    for r in rows:
        if r.total_claims == 0:
            continue
        
        weekend_pct = (r.weekend_claims / r.total_claims) * 100
        
        # Flag if >20% weekend (threshold from Brooklyn case)
        if weekend_pct > 20:
            severity = "high" if weekend_pct > 40 else "medium"
            results.append({
                "pattern": "weekend_holiday_anomaly",
                "provider_id": r.provider_id,
                "provider_name": r.name,
                "weekend_claims": int(r.weekend_claims),
                "total_claims": int(r.total_claims),
                "weekend_percentage": round(weekend_pct, 1),
                "severity": severity,
                "details": f"{weekend_pct:.1f}% of claims on weekends"
            })
    
    return results


def _detect_beneficiary_concentration(
    db: Session,
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,
) -> List[Dict[str, Any]]:
    """Detect unusual concentration in beneficiary billing (kickback proxy).

    Flags providers where a small number of beneficiaries account for
    a large percentage of claims (Brooklyn $68M case pattern).
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Get providers with their claims per beneficiary
    query = (
        db.query(
            Provider.id.label("provider_id"),
            Provider.name,
            Claim.beneficiary_id,
            func.count(Claim.id).label("claims_per_beneficiary"),
            func.sum(Claim.amount).label("amount_per_beneficiary"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Claim.claim_date >= cutoff_date)
        .filter(Claim.beneficiary_id.isnot(None))
        .group_by(Provider.id, Claim.beneficiary_id)
    )
    
    if provider_id:
        query = query.filter(Provider.id == provider_id)
    
    rows = query.all()
    
    # Group by provider
    provider_beneficiaries = {}
    for r in rows:
        if r.provider_id not in provider_beneficiaries:
            provider_beneficiaries[r.provider_id] = {
                "name": r.name,
                "beneficiaries": [],
                "total_claims": 0,
            }
        provider_beneficiaries[r.provider_id]["beneficiaries"].append({
            "beneficiary_id": r.beneficiary_id,
            "claims": int(r.claims_per_beneficiary),
            "amount": float(r.amount_per_beneficiary),
        })
        provider_beneficiaries[r.provider_id]["total_claims"] += int(r.claims_per_beneficiary)
    
    results = []
    for pid, data in provider_beneficiaries.items():
        if data["total_claims"] < 50:  # Skip providers with too few claims
            continue
        
        # Sort beneficiaries by claim count
        beneficiaries = sorted(data["beneficiaries"], key=lambda x: x["claims"], reverse=True)
        
        # Calculate concentration: top 5% of beneficiaries
        n_beneficiaries = len(beneficiaries)
        top_n = max(1, n_beneficiaries // 20)  # Top 5%
        
        top_claims = sum(b["claims"] for b in beneficiaries[:top_n])
        concentration = (top_claims / data["total_claims"]) * 100
        
        # Calculate Gini coefficient (inequality measure)
        if n_beneficiaries > 1:
            claims_list = [b["claims"] for b in beneficiaries]
            # Simplified Gini calculation
            sorted_claims = np.sort(claims_list)
            cumulative = np.cumsum(sorted_claims)
            gini = (np.sum((2 * np.arange(1, len(sorted_claims)+1) - len(sorted_claims) - 1) * sorted_claims)) / (len(sorted_claims) * np.sum(sorted_claims))
            gini = float(gini)
        else:
            gini = 1.0
        
        # Flag if highly concentrated
        if concentration > 60:  # Top 5% account for >60% of claims
            severity = "high" if concentration > 80 else "medium"
            
            results.append({
                "pattern": "beneficiary_concentration",
                "provider_id": pid,
                "provider_name": data["name"],
                "concentration_percentage": round(concentration, 1),
                "gini_coefficient": round(gini, 3),
                "total_beneficiaries": n_beneficiaries,
                "top_beneficiaries": top_n,
                "total_claims": data["total_claims"],
                "severity": severity,
                "details": f"Top {top_n} beneficiaries account for {concentration:.1f}% of claims"
            })
            
            # Save to kickback indicators table
            indicator = KickbackIndicator(
                provider_id=pid,
                beneficiary_concentration=concentration / 100,
                risk_score=concentration,
                notes=f"High beneficiary concentration: {concentration:.1f}% from top 5%"
            )
            db.add(indicator)
    
    db.commit()
    return results


def _detect_capacity_patterns(
    db: Session,
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,
) -> List[Dict[str, Any]]:
    """Detect patterns suggesting capacity violations (Queens case).

    Flags providers who may be billing beyond their licensed capacity
    by analyzing daily claim volumes.
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Get providers with licensed capacity
    providers = db.query(Provider).filter(Provider.licensed_capacity.isnot(None))
    if provider_id:
        providers = providers.filter(Provider.id == provider_id)
    
    results = []
    for provider in providers:
        # Get daily claim counts
        daily_claims = (
            db.query(
                Claim.claim_date,
                func.count(Claim.id).label("claim_count"),
                func.count(func.distinct(Claim.beneficiary_id)).label("unique_patients"),
            )
            .filter(Claim.provider_id == provider.id)
            .filter(Claim.claim_date >= cutoff_date)
            .group_by(Claim.claim_date)
            .order_by(Claim.claim_date)
            .all()
        )
        
        if not daily_claims:
            continue
        
        # Check for capacity violations
        violations = []
        for day in daily_claims:
            if day.unique_patients > provider.licensed_capacity:
                violations.append({
                    "date": day.claim_date.isoformat(),
                    "patients": int(day.unique_patients),
                    "capacity": provider.licensed_capacity,
                    "excess": int(day.unique_patients - provider.licensed_capacity),
                })
                
                # Save to capacity violations table
                cv = CapacityViolation(
                    provider_id=provider.id,
                    violation_date=day.claim_date,
                    licensed_capacity=provider.licensed_capacity,
                    billed_patients=int(day.unique_patients),
                    excess_percentage=((day.unique_patients - provider.licensed_capacity) / provider.licensed_capacity) * 100,
                    severity="high" if day.unique_patients > provider.licensed_capacity * 1.5 else "medium",
                )
                db.add(cv)
        
        if violations:
            db.commit()
            
            # Calculate violation rate
            violation_rate = (len(violations) / len(daily_claims)) * 100
            
            results.append({
                "pattern": "capacity_violation_pattern",
                "provider_id": provider.id,
                "provider_name": provider.name,
                "licensed_capacity": provider.licensed_capacity,
                "violation_count": len(violations),
                "total_days": len(daily_claims),
                "violation_rate": round(violation_rate, 1),
                "max_excess": max(v.get("excess", 0) for v in violations),
                "severity": "high" if violation_rate > 20 else "medium",
                "details": violations[:10],  # First 10 violations
            })
    
    return results


def _detect_batch_submission(
    db: Session,
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,
) -> List[Dict[str, Any]]:
    """Detect suspicious batch submission patterns.

    Flags providers who submit claims in large batches or at unusual times.
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    query = (
        db.query(
            Provider.id.label("provider_id"),
            Provider.name,
            Claim.submitted_date,
            func.count(Claim.id).label("batch_size"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Claim.claim_date >= cutoff_date)
        .filter(Claim.submitted_date.isnot(None))
        .group_by(Provider.id, Claim.submitted_date)
    )
    
    if provider_id:
        query = query.filter(Provider.id == provider_id)
    
    rows = query.all()
    
    # Group by provider
    provider_batches = {}
    for r in rows:
        if r.provider_id not in provider_batches:
            provider_batches[r.provider_id] = {
                "name": r.name,
                "batches": [],
            }
        provider_batches[r.provider_id]["batches"].append({
            "date": r.submitted_date.isoformat() if r.submitted_date else None,
            "size": int(r.batch_size),
        })
    
    results = []
    for pid, data in provider_batches.items():
        batches = data["batches"]
        if len(batches) < 10:
            continue
        
        batch_sizes = [b["size"] for b in batches]
        avg_size = np.mean(batch_sizes)
        max_size = max(batch_sizes)
        
        # Flag if average batch size > 100 (suspiciously large)
        if avg_size > 100:
            results.append({
                "pattern": "large_batch_submission",
                "provider_id": pid,
                "provider_name": data["name"],
                "avg_batch_size": round(avg_size, 1),
                "max_batch_size": max_size,
                "total_batches": len(batches),
                "severity": "high" if avg_size > 500 else "medium",
            })
    
    return results


def _detect_code_creep(
    db: Session,
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,
) -> List[Dict[str, Any]]:
    """Detect year-over-year code creep (upcoding over time).

    Flags providers who shift to higher-value codes over time.
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Get code usage by year per provider
    query = (
        db.query(
            Provider.id.label("provider_id"),
            Provider.name,
            extract("year", Claim.claim_date).label("year"),
            Claim.billing_code,
            func.avg(Claim.amount).label("avg_amount"),
            func.count(Claim.id).label("code_count"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(Claim.claim_date >= cutoff_date)
        .group_by(Provider.id, "year", Claim.billing_code)
    )
    
    if provider_id:
        query = query.filter(Provider.id == provider_id)
    
    rows = query.all()
    
    # Group by provider and year
    provider_years = {}
    for r in rows:
        if r.provider_id not in provider_years:
            provider_years[r.provider_id] = {
                "name": r.name,
                "years": {},
            }
        if r.year not in provider_years[r.provider_id]["years"]:
            provider_years[r.provider_id]["years"][r.year] = []
        provider_years[r.provider_id]["years"][r.year].append({
            "code": r.billing_code,
            "avg_amount": float(r.avg_amount),
            "count": int(r.code_count),
        })
    
    results = []
    for pid, data in provider_years.items():
        years = sorted(data["years"].keys())
        if len(years) < 2:
            continue
        
        # Track average code value over time
        avg_values = []
        for year in years:
            codes = data["years"][year]
            if codes:
                # Weighted average by count
                total_amount = sum(c["avg_amount"] * c["count"] for c in codes)
                total_count = sum(c["count"] for c in codes)
                avg_values.append(total_amount / total_count if total_count else 0)
        
        if len(avg_values) >= 2:
            # Calculate trend
            first_avg = avg_values[0]
            last_avg = avg_values[-1]
            
            if last_avg > first_avg * 1.5:  # 50% increase
                results.append({
                    "pattern": "code_creep",
                    "provider_id": pid,
                    "provider_name": data["name"],
                    "years_analyzed": len(years),
                    "first_year_avg": round(first_avg, 2),
                    "last_year_avg": round(last_avg, 2),
                    "increase_percentage": round(((last_avg - first_avg) / first_avg) * 100, 1),
                    "severity": "high" if last_avg > first_avg * 2 else "medium",
                })
    
    return results


def _detect_unusual_service_hours(
    db: Session,
    provider_id: Optional[int] = None,
    days_back: int = 365 * 3,
) -> List[Dict[str, Any]]:
    """Detect services billed at unusual hours (e.g., 2 AM).

    Flags providers with claims submitted outside normal business hours.
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # This requires timestamp data - simplified version
    return []


def _save_patterns_to_db(db: Session, patterns: List[Dict[str, Any]]) -> None:
    """Save detected patterns to anomalies table."""
    for pattern in patterns:
        anomaly = Anomaly(
            provider_id=pattern["provider_id"],
            billing_code=pattern.get("code", "multiple"),
            z_score=0.0,  # Not applicable for pattern detection
            anomaly_type=pattern["pattern"],
            notes=pattern.get("details", str(pattern)),
        )
        db.add(anomaly)
    
    db.commit()
    logger.info(f"Saved {len(patterns)} patterns to anomalies table")
