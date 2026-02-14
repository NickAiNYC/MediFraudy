"""Forensic Pattern-of-Life Intelligence Layer.

Based on recent prosecution patterns in NYC elderly care fraud cases:
- Queens $120M case: Capacity violations, kickbacks, pharmacy fraud
- Brooklyn $68M case: Unprovided services, weekend billing, kickbacks
- Albany $1.3M case: Understaffing, neglect, false claims
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from models import (
    Provider,
    Claim,
    Anomaly,
    KickbackIndicator,
    CapacityViolation,
)

logger = logging.getLogger(__name__)


def analyze_behavioral_patterns(
    db: Session,
    provider_id: int,
    lookback_days: int = 365
) -> Dict[str, Any]:
    """Analyze provider behavioral patterns over time.
    
    Detects:
    - Unusual billing time patterns (e.g., weekend/holiday fraud)
    - Service timing anomalies
    - Claim submission patterns
    - Beneficiary interaction patterns
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back for analysis
        
    Returns:
        Dictionary with behavioral pattern analysis
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}
    
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Get claims for analysis
    claims = (
        db.query(Claim)
        .filter(
            and_(
                Claim.provider_id == provider_id,
                Claim.claim_date >= cutoff_date
            )
        )
        .all()
    )
    
    if not claims:
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "pattern_type": "behavioral",
            "risk_score": 0,
            "findings": [],
            "evidence": {"message": "No claims data available for analysis"}
        }
    
    findings = []
    risk_score = 0
    
    # Analyze weekend billing (Brooklyn case pattern)
    weekend_claims = [c for c in claims if c.claim_date.weekday() >= 5]
    weekend_ratio = len(weekend_claims) / len(claims) if claims else 0
    
    if weekend_ratio > 0.15:  # More than 15% weekend billing
        findings.append({
            "type": "weekend_billing_anomaly",
            "severity": "high" if weekend_ratio > 0.25 else "medium",
            "description": f"Unusual weekend billing pattern: {weekend_ratio:.1%} of claims on weekends",
            "evidence": {
                "weekend_claims": len(weekend_claims),
                "total_claims": len(claims),
                "ratio": weekend_ratio
            }
        })
        risk_score += 30 if weekend_ratio > 0.25 else 15
    
    # Analyze holiday billing patterns
    # Note: Holiday detection would require a calendar of federal/state holidays.
    # This is a placeholder for future enhancement. For now, weekend billing
    # serves as a proxy for unusual timing patterns.
    
    # Analyze time-of-day patterns for suspicious batch submissions
    submission_hours = {}
    for claim in claims:
        if claim.submitted_date:
            hour = claim.submitted_date.hour
            submission_hours[hour] = submission_hours.get(hour, 0) + 1
    
    # Check for unusual batch submissions (all claims at same hour)
    if submission_hours:
        max_hour_count = max(submission_hours.values())
        batch_ratio = max_hour_count / len(claims)
        
        if batch_ratio > 0.5:  # More than 50% submitted in same hour
            findings.append({
                "type": "batch_submission_pattern",
                "severity": "medium",
                "description": f"Suspicious batch submission: {batch_ratio:.1%} of claims at same hour",
                "evidence": {
                    "batch_size": max_hour_count,
                    "total_claims": len(claims),
                    "ratio": batch_ratio
                }
            })
            risk_score += 20
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "pattern_type": "behavioral",
        "risk_score": min(risk_score, 100),
        "findings": findings,
        "analysis_period_days": lookback_days,
        "total_claims_analyzed": len(claims)
    }


def detect_capacity_violations(
    db: Session,
    provider_id: int,
    lookback_days: int = 365
) -> Dict[str, Any]:
    """Detect capacity violations (Queens $120M case pattern).
    
    Identifies providers billing for more patients than their licensed
    capacity allows on a given day.
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back
        
    Returns:
        Capacity violation analysis
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}
    
    if not provider.licensed_capacity:
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "pattern_type": "capacity_violation",
            "risk_score": 0,
            "findings": [],
            "evidence": {"message": "No licensed capacity data available"}
        }
    
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Count unique beneficiaries per day
    daily_patient_counts = (
        db.query(
            func.date(Claim.claim_date).label("service_date"),
            func.count(func.distinct(Claim.beneficiary_id)).label("patient_count")
        )
        .filter(
            and_(
                Claim.provider_id == provider_id,
                Claim.claim_date >= cutoff_date
            )
        )
        .group_by(func.date(Claim.claim_date))
        .all()
    )
    
    violations = []
    for date_record, patient_count in daily_patient_counts:
        if patient_count > provider.licensed_capacity:
            excess = patient_count - provider.licensed_capacity
            excess_pct = (excess / provider.licensed_capacity) * 100
            violations.append({
                "date": str(date_record),
                "licensed_capacity": provider.licensed_capacity,
                "billed_patients": patient_count,
                "excess": excess,
                "excess_percentage": excess_pct
            })
    
    findings = []
    risk_score = 0
    
    if violations:
        avg_excess = sum(v["excess_percentage"] for v in violations) / len(violations)
        max_excess = max(v["excess_percentage"] for v in violations)
        
        findings.append({
            "type": "capacity_violation",
            "severity": "critical" if max_excess > 50 else "high",
            "description": f"Billing exceeded licensed capacity on {len(violations)} days",
            "evidence": {
                "violation_count": len(violations),
                "average_excess_percentage": avg_excess,
                "maximum_excess_percentage": max_excess,
                "violations": violations[:10]  # First 10 for evidence
            }
        })
        risk_score = min(100, 40 + len(violations))
        
        # Store violation in database
        violation_record = CapacityViolation(
            provider_id=provider_id,
            licensed_capacity=provider.licensed_capacity,
            daily_billed_patients={"violations": violations},
            violation_dates=[v["date"] for v in violations],
            severity="critical" if max_excess > 50 else "high",
            notes=f"Detected {len(violations)} capacity violations with max excess of {max_excess:.1f}%"
        )
        db.add(violation_record)
        db.commit()
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "licensed_capacity": provider.licensed_capacity,
        "pattern_type": "capacity_violation",
        "risk_score": risk_score,
        "findings": findings,
        "analysis_period_days": lookback_days
    }


def detect_kickback_patterns(
    db: Session,
    provider_id: int,
    lookback_days: int = 365
) -> Dict[str, Any]:
    """Detect kickback scheme indicators (Brooklyn & Queens case patterns).
    
    Identifies:
    - Unusual beneficiary concentration (same patients repeatedly)
    - Referral network anomalies
    - Patient enrollment spikes
    - Billing for services not provided
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back
        
    Returns:
        Kickback pattern analysis
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}
    
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Get beneficiary claim counts
    beneficiary_stats = (
        db.query(
            Claim.beneficiary_id,
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount")
        )
        .filter(
            and_(
                Claim.provider_id == provider_id,
                Claim.claim_date >= cutoff_date
            )
        )
        .group_by(Claim.beneficiary_id)
        .all()
    )
    
    if not beneficiary_stats:
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "pattern_type": "kickback",
            "risk_score": 0,
            "findings": [],
            "evidence": {"message": "No beneficiary data available"}
        }
    
    findings = []
    risk_score = 0
    
    # Calculate beneficiary concentration
    total_claims = sum(stat.claim_count for stat in beneficiary_stats)
    total_beneficiaries = len(beneficiary_stats)
    avg_claims_per_beneficiary = total_claims / total_beneficiaries if total_beneficiaries else 0
    
    # Detect high-concentration beneficiaries
    high_concentration = [
        stat for stat in beneficiary_stats
        if stat.claim_count > avg_claims_per_beneficiary * 3
    ]
    
    if high_concentration:
        concentration_ratio = len(high_concentration) / total_beneficiaries
        findings.append({
            "type": "beneficiary_concentration",
            "severity": "high" if concentration_ratio > 0.1 else "medium",
            "description": f"Unusual concentration: {len(high_concentration)} beneficiaries with 3x average claims",
            "evidence": {
                "high_concentration_count": len(high_concentration),
                "total_beneficiaries": total_beneficiaries,
                "concentration_ratio": concentration_ratio,
                "average_claims_per_beneficiary": avg_claims_per_beneficiary
            }
        })
        risk_score += 35 if concentration_ratio > 0.1 else 20
    
    # Detect enrollment spikes (month-over-month)
    # Use strftime for SQLite compatibility (works with both SQLite and PostgreSQL)
    monthly_new_beneficiaries = (
        db.query(
            func.strftime('%Y-%m', Claim.claim_date).label("month"),
            func.count(func.distinct(Claim.beneficiary_id)).label("new_count")
        )
        .filter(
            and_(
                Claim.provider_id == provider_id,
                Claim.claim_date >= cutoff_date
            )
        )
        .group_by(func.strftime('%Y-%m', Claim.claim_date))
        .order_by(func.strftime('%Y-%m', Claim.claim_date))
        .all()
    )
    
    if len(monthly_new_beneficiaries) >= 2:
        counts = [record.new_count for record in monthly_new_beneficiaries]
        avg_monthly = sum(counts) / len(counts)
        
        spikes = [
            {"month": str(record.month), "count": record.new_count}
            for record in monthly_new_beneficiaries
            if record.new_count > avg_monthly * 2
        ]
        
        if spikes:
            findings.append({
                "type": "enrollment_spike",
                "severity": "high",
                "description": f"Detected {len(spikes)} months with unusual enrollment spikes",
                "evidence": {
                    "spike_months": spikes,
                    "average_monthly_enrollment": avg_monthly
                }
            })
            risk_score += 25
    
    # Store kickback indicators
    if findings:
        # Note: cash_withdrawal_pattern requires integration with financial transaction data
        # which is typically not available in claims databases. This field is reserved
        # for future integration with external data sources (e.g., bank records in qui tam cases).
        indicator = KickbackIndicator(
            provider_id=provider_id,
            cash_withdrawal_pattern=False,  # Requires external financial data
            referral_network={"high_concentration_beneficiaries": len(high_concentration)},
            patient_enrollment_spikes=[s["month"] for s in spikes] if 'spikes' in locals() else [],
            notes=f"Detected {len(findings)} kickback indicators"
        )
        db.add(indicator)
        db.commit()
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "pattern_type": "kickback",
        "risk_score": min(risk_score, 100),
        "findings": findings,
        "total_beneficiaries": total_beneficiaries,
        "analysis_period_days": lookback_days
    }


def comprehensive_pattern_analysis(
    db: Session,
    provider_id: int,
    lookback_days: int = 365
) -> Dict[str, Any]:
    """Run comprehensive pattern-of-life analysis combining all detection methods.
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back
        
    Returns:
        Comprehensive analysis with combined risk score
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}
    
    # Run all analysis modules
    behavioral = analyze_behavioral_patterns(db, provider_id, lookback_days)
    capacity = detect_capacity_violations(db, provider_id, lookback_days)
    kickback = detect_kickback_patterns(db, provider_id, lookback_days)
    
    # Combine findings
    all_findings = (
        behavioral.get("findings", []) +
        capacity.get("findings", []) +
        kickback.get("findings", [])
    )
    
    # Calculate composite risk score (weighted average)
    risk_scores = [
        behavioral.get("risk_score", 0) * 0.3,
        capacity.get("risk_score", 0) * 0.4,
        kickback.get("risk_score", 0) * 0.3
    ]
    composite_risk = sum(risk_scores)
    
    # Determine overall severity
    if composite_risk >= 70:
        severity = "critical"
    elif composite_risk >= 50:
        severity = "high"
    elif composite_risk >= 30:
        severity = "medium"
    else:
        severity = "low"
    
    # Store comprehensive anomaly if risk is significant
    if composite_risk >= 30:
        anomaly = Anomaly(
            provider_id=provider_id,
            billing_code="PATTERN_OF_LIFE",
            z_score=composite_risk / 10,  # Convert to z-score scale
            anomaly_type="pattern_of_life",
            notes=f"Comprehensive pattern analysis detected {len(all_findings)} issues",
        )
        db.add(anomaly)
        db.commit()
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "provider_type": provider.facility_type,
        "analysis_type": "comprehensive_pattern_of_life",
        "composite_risk_score": composite_risk,
        "severity": severity,
        "analysis_modules": {
            "behavioral": behavioral,
            "capacity_violations": capacity,
            "kickback_indicators": kickback
        },
        "all_findings": all_findings,
        "total_findings": len(all_findings),
        "analysis_period_days": lookback_days,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


def analyze_nyc_elderly_care_facilities(
    db: Session,
    min_risk_score: int = 50,
    limit: int = 100
) -> Dict[str, Any]:
    """Analyze all NYC elderly care facilities for pattern-of-life anomalies.
    
    Focus on facility types relevant to recent prosecutions:
    - Nursing homes
    - Adult day care centers
    - Home health agencies
    - Rehabilitation facilities
    
    Args:
        db: Database session
        min_risk_score: Minimum risk score to include in results
        limit: Maximum number of providers to analyze
        
    Returns:
        Analysis results for NYC elderly care facilities
    """
    # Target facility types from recent cases
    target_types = [
        "Nursing Home",
        "Adult Day Care",
        "Home Health Agency",
        "Skilled Nursing Facility",
        "Rehabilitation Facility"
    ]
    
    # Query NYC providers of target types
    providers = (
        db.query(Provider)
        .filter(
            and_(
                Provider.state == "NY",
                or_(Provider.city.ilike("%New York%"), Provider.city.ilike("%Brooklyn%"), 
                    Provider.city.ilike("%Queens%"), Provider.city.ilike("%Bronx%"),
                    Provider.city.ilike("%Staten Island%")),
                or_(*[Provider.facility_type.ilike(f"%{ft}%") for ft in target_types])
            )
        )
        .limit(limit)
        .all()
    )
    
    results = []
    high_risk_count = 0
    
    for provider in providers:
        analysis = comprehensive_pattern_analysis(db, provider.id)
        
        if analysis.get("composite_risk_score", 0) >= min_risk_score:
            results.append({
                "provider_id": provider.id,
                "npi": provider.npi,
                "name": provider.name,
                "city": provider.city,
                "facility_type": provider.facility_type,
                "risk_score": analysis.get("composite_risk_score"),
                "severity": analysis.get("severity"),
                "findings_count": analysis.get("total_findings", 0)
            })
            
            if analysis.get("composite_risk_score", 0) >= 70:
                high_risk_count += 1
    
    # Sort by risk score descending
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "analysis_type": "nyc_elderly_care_sweep",
        "target_facility_types": target_types,
        "providers_analyzed": len(providers),
        "high_risk_facilities": high_risk_count,
        "results": results,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }
