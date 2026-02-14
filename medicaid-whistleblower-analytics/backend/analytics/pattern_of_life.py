"""Forensic Pattern-of-Life Intelligence Layer.

Based on recent prosecution patterns in NYC elderly care fraud cases:
- Queens $120M case: Capacity violations, kickbacks, pharmacy fraud
- Brooklyn $68M case: Unprovided services, weekend billing, kickbacks
- Albany $1.3M case: Understaffing, neglect, false claims

This module provides behavioral fingerprinting to detect intent,
not just statistical outliers.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from models import (
    Provider,
    Claim,
    Anomaly,
    KickbackIndicator,
    CapacityViolation,
    POLResult,
)

logger = logging.getLogger(__name__)

# Constants for scoring thresholds (calibrated from prosecuted cases)
THRESHOLDS = {
    "weekend_high": 0.25,      # >25% weekend claims = critical
    "weekend_medium": 0.15,     # >15% weekend claims = high
    "capacity_high": 50,        # >50% excess capacity = critical
    "capacity_medium": 20,       # >20% excess = high
    "concentration_high": 0.8,   # Top 5% patients account for >80% = critical
    "concentration_medium": 0.6, # >60% = high
    "spike_factor": 2.5,         # >2.5x average = spike
    "batch_high": 0.7,           # >70% same hour = critical
    "batch_medium": 0.5,         # >50% same hour = high
}

# Weights for composite scoring (must sum to 1.0)
WEIGHTS = {
    "capacity": 0.40,    # Queens case
    "kickback": 0.35,    # Brooklyn case
    "behavioral": 0.25,  # General fraud indicators
}


def analyze_behavioral_patterns(
    db: Session,
    provider_id: int,
    lookback_days: int = 365
) -> Dict[str, Any]:
    """Analyze provider behavioral patterns over time.
    
    Detects:
    - Unusual billing time patterns (weekend/holiday fraud - Brooklyn case)
    - Service timing anomalies
    - Claim submission patterns
    - Beneficiary interaction patterns
    - Robotic billing (same codes, same amounts, same intervals)
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back for analysis
        
    Returns:
        Dictionary with behavioral pattern analysis and risk score (0-100)
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found", "risk_score": 0}
    
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
        .order_by(Claim.claim_date)
        .all()
    )
    
    if not claims:
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "pattern_type": "behavioral",
            "risk_score": 0,
            "risk_level": "LOW",
            "findings": [],
            "evidence": {"message": "No claims data available for analysis"}
        }
    
    findings = []
    risk_score = 0
    evidence = {}
    
    # -----------------------------------------------------------------------
    # 1. Weekend billing analysis (Brooklyn case pattern)
    # -----------------------------------------------------------------------
    weekend_claims = [c for c in claims if c.claim_date.weekday() >= 5]
    weekend_ratio = len(weekend_claims) / len(claims) if claims else 0
    evidence["weekend_ratio"] = weekend_ratio
    
    if weekend_ratio > THRESHOLDS["weekend_high"]:
        findings.append({
            "type": "weekend_billing_anomaly",
            "severity": "critical",
            "description": f"Extreme weekend billing: {weekend_ratio:.1%} of claims on weekends",
            "evidence": {
                "weekend_claims": len(weekend_claims),
                "total_claims": len(claims),
                "ratio": weekend_ratio,
                "threshold": THRESHOLDS["weekend_high"]
            }
        })
        risk_score += 40
    elif weekend_ratio > THRESHOLDS["weekend_medium"]:
        findings.append({
            "type": "weekend_billing_anomaly",
            "severity": "high",
            "description": f"Elevated weekend billing: {weekend_ratio:.1%} of claims on weekends",
            "evidence": {
                "weekend_claims": len(weekend_claims),
                "total_claims": len(claims),
                "ratio": weekend_ratio,
                "threshold": THRESHOLDS["weekend_medium"]
            }
        })
        risk_score += 25
    
    # -----------------------------------------------------------------------
    # 2. Holiday billing (if we had holiday calendar)
    # -----------------------------------------------------------------------
    # Placeholder for future enhancement
    
    # -----------------------------------------------------------------------
    # 3. Batch submission patterns (suspicious automated billing)
    # -----------------------------------------------------------------------
    if claims and claims[0].submitted_date is not None:
        submission_hours = {}
        for claim in claims:
            if claim.submitted_date:
                hour = claim.submitted_date.hour
                submission_hours[hour] = submission_hours.get(hour, 0) + 1
        
        if submission_hours:
            max_hour_count = max(submission_hours.values())
            batch_ratio = max_hour_count / len(claims)
            evidence["batch_ratio"] = batch_ratio
            
            if batch_ratio > THRESHOLDS["batch_high"]:
                findings.append({
                    "type": "batch_submission_pattern",
                    "severity": "critical",
                    "description": f"Extreme batch submission: {batch_ratio:.1%} of claims in same hour",
                    "evidence": {
                        "peak_hour": max(submission_hours.items(), key=lambda x: x[1])[0],
                        "batch_size": max_hour_count,
                        "total_claims": len(claims),
                        "ratio": batch_ratio
                    }
                })
                risk_score += 30
            elif batch_ratio > THRESHOLDS["batch_medium"]:
                findings.append({
                    "type": "batch_submission_pattern",
                    "severity": "high",
                    "description": f"Suspicious batch submission: {batch_ratio:.1%} of claims in same hour",
                    "evidence": {
                        "peak_hour": max(submission_hours.items(), key=lambda x: x[1])[0],
                        "batch_size": max_hour_count,
                        "total_claims": len(claims),
                        "ratio": batch_ratio
                    }
                })
                risk_score += 20
    
    # -----------------------------------------------------------------------
    # 4. Robotic billing detection (same codes, same amounts)
    # -----------------------------------------------------------------------
    # Group by code and amount
    code_amount_pairs = {}
    for claim in claims:
        key = f"{claim.billing_code}_{claim.amount}"
        code_amount_pairs[key] = code_amount_pairs.get(key, 0) + 1
    
    if code_amount_pairs:
        # Find most common pair
        max_pair_count = max(code_amount_pairs.values())
        robotic_ratio = max_pair_count / len(claims)
        evidence["robotic_ratio"] = robotic_ratio
        
        if robotic_ratio > 0.3:  # >30% identical code+amount
            findings.append({
                "type": "robotic_billing_pattern",
                "severity": "high" if robotic_ratio > 0.5 else "medium",
                "description": f"Repetitive billing pattern: {robotic_ratio:.1%} of claims identical",
                "evidence": {
                    "identical_pairs": max_pair_count,
                    "total_claims": len(claims),
                    "ratio": robotic_ratio
                }
            })
            risk_score += 15 if robotic_ratio > 0.5 else 10
    
    # -----------------------------------------------------------------------
    # 5. Service time consistency (claims always same day of week)
    # -----------------------------------------------------------------------
    dow_counts = {}
    for claim in claims:
        dow = claim.claim_date.weekday()
        dow_counts[dow] = dow_counts.get(dow, 0) + 1
    
    if dow_counts:
        max_dow_count = max(dow_counts.values())
        dow_ratio = max_dow_count / len(claims)
        evidence["dow_concentration"] = dow_ratio
        
        if dow_ratio > 0.4:  # >40% on same day of week
            findings.append({
                "type": "day_of_week_concentration",
                "severity": "medium",
                "description": f"Unusual concentration: {dow_ratio:.1%} of claims on same weekday",
                "evidence": {
                    "peak_dow": max(dow_counts.items(), key=lambda x: x[1])[0],
                    "peak_count": max_dow_count,
                    "total_claims": len(claims),
                    "ratio": dow_ratio
                }
            })
            risk_score += 10
    
    # Normalize risk score to 0-100 scale
    risk_score = min(100, risk_score)
    
    # Determine risk level
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "pattern_type": "behavioral",
        "risk_score": risk_score,
        "risk_level": risk_level,
        "findings": findings,
        "evidence": evidence,
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
    capacity allows on a given day. Returns risk score 0-100.
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back
        
    Returns:
        Capacity violation analysis with risk score
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found", "risk_score": 0}
    
    if not provider.licensed_capacity:
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "pattern_type": "capacity_violation",
            "risk_score": 0,
            "risk_level": "LOW",
            "findings": [],
            "evidence": {"message": "No licensed capacity data available"}
        }
    
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Count unique beneficiaries per day
    # Note: This assumes each beneficiary represents a unique patient
    # For more accuracy, you'd need to deduplicate by patient identifier
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
        .order_by(func.date(Claim.claim_date))
        .all()
    )
    
    if not daily_patient_counts:
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "pattern_type": "capacity_violation",
            "risk_score": 0,
            "risk_level": "LOW",
            "findings": [],
            "evidence": {"message": "No claims data for capacity analysis"}
        }
    
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
                "excess_percentage": round(excess_pct, 1)
            })
    
    findings = []
    risk_score = 0
    evidence = {
        "total_days_analyzed": len(daily_patient_counts),
        "violation_days": len(violations)
    }
    
    if violations:
        # Calculate statistics
        avg_excess = sum(v["excess_percentage"] for v in violations) / len(violations)
        max_excess = max(v["excess_percentage"] for v in violations)
        violation_rate = (len(violations) / len(daily_patient_counts)) * 100
        
        evidence.update({
            "average_excess_percentage": round(avg_excess, 1),
            "maximum_excess_percentage": round(max_excess, 1),
            "violation_rate": round(violation_rate, 1)
        })
        
        # Determine severity based on Queens case patterns
        if max_excess > THRESHOLDS["capacity_high"] or violation_rate > 30:
            severity = "critical"
            risk_score = 90
        elif max_excess > THRESHOLDS["capacity_medium"] or violation_rate > 15:
            severity = "high"
            risk_score = 70
        else:
            severity = "medium"
            risk_score = 50
        
        findings.append({
            "type": "capacity_violation",
            "severity": severity,
            "description": f"Billing exceeded licensed capacity on {len(violations)} days ({violation_rate:.1f}% of operating days)",
            "evidence": {
                "violation_count": len(violations),
                "violation_rate": round(violation_rate, 1),
                "average_excess_percentage": round(avg_excess, 1),
                "maximum_excess_percentage": round(max_excess, 1),
                "sample_violations": violations[:5]  # First 5 as evidence
            }
        })
        
        # Store violation in database
        for violation in violations[:20]:  # Store up to 20 violations
            violation_record = CapacityViolation(
                provider_id=provider_id,
                violation_date=datetime.fromisoformat(violation["date"]),
                licensed_capacity=violation["licensed_capacity"],
                billed_patients=violation["billed_patients"],
                excess_percentage=violation["excess_percentage"],
                severity=severity
            )
            db.add(violation_record)
        
        db.commit()
        logger.info(f"Stored {min(len(violations), 20)} capacity violations for provider {provider_id}")
    
    # Determine risk level
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "licensed_capacity": provider.licensed_capacity,
        "pattern_type": "capacity_violation",
        "risk_score": risk_score,
        "risk_level": risk_level,
        "findings": findings,
        "evidence": evidence,
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
    - Billing for services not provided (proxied by robotic patterns)
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back
        
    Returns:
        Kickback pattern analysis with risk score 0-100
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found", "risk_score": 0}
    
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Get beneficiary claim counts
    beneficiary_stats = (
        db.query(
            Claim.beneficiary_id,
            func.count(Claim.id).label("claim_count"),
            func.sum(Claim.amount).label("total_amount"),
            func.min(Claim.claim_date).label("first_claim"),
            func.max(Claim.claim_date).label("last_claim")
        )
        .filter(
            and_(
                Claim.provider_id == provider_id,
                Claim.claim_date >= cutoff_date
            )
        )
        .group_by(Claim.beneficiary_id)
        .having(func.count(Claim.id) >= 3)  # At least 3 claims to be meaningful
        .all()
    )
    
    if not beneficiary_stats or len(beneficiary_stats) < 3:
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "pattern_type": "kickback",
            "risk_score": 0,
            "risk_level": "LOW",
            "findings": [],
            "evidence": {"message": "Insufficient beneficiary data for analysis"}
        }
    
    findings = []
    risk_score = 0
    evidence = {}
    
    # -----------------------------------------------------------------------
    # 1. Beneficiary concentration analysis (kickback proxy)
    # -----------------------------------------------------------------------
    total_claims = sum(stat.claim_count for stat in beneficiary_stats)
    total_beneficiaries = len(beneficiary_stats)
    evidence["total_beneficiaries"] = total_beneficiaries
    evidence["total_claims"] = total_claims
    
    # Sort by claim count
    sorted_stats = sorted(beneficiary_stats, key=lambda x: x.claim_count, reverse=True)
    
    # Calculate concentration: top 5% of beneficiaries
    top_n = max(1, total_beneficiaries // 20)  # Top 5%
    top_claims = sum(stat.claim_count for stat in sorted_stats[:top_n])
    concentration = (top_claims / total_claims) if total_claims > 0 else 0
    evidence["concentration_ratio"] = concentration
    
    # Calculate Gini coefficient (inequality measure)
    if total_beneficiaries > 1:
        claim_counts = [stat.claim_count for stat in sorted_stats]
        # Normalized Gini calculation
        sorted_counts = np.sort(claim_counts)
        cumulative = np.cumsum(sorted_counts)
        gini = (np.sum((2 * np.arange(1, len(sorted_counts)+1) - len(sorted_counts) - 1) * sorted_counts)) / (len(sorted_counts) * np.sum(sorted_counts))
        evidence["gini_coefficient"] = float(gini)
    else:
        gini = 1.0
        evidence["gini_coefficient"] = 1.0
    
    # Score based on concentration
    if concentration > THRESHOLDS["concentration_high"]:
        findings.append({
            "type": "beneficiary_concentration",
            "severity": "critical",
            "description": f"Extreme concentration: top {top_n} patients account for {concentration:.1%} of claims",
            "evidence": {
                "concentration_ratio": concentration,
                "gini_coefficient": gini,
                "top_patients_count": top_n,
                "total_patients": total_beneficiaries,
                "threshold": THRESHOLDS["concentration_high"]
            }
        })
        risk_score += 45
    elif concentration > THRESHOLDS["concentration_medium"]:
        findings.append({
            "type": "beneficiary_concentration",
            "severity": "high",
            "description": f"High concentration: top {top_n} patients account for {concentration:.1%} of claims",
            "evidence": {
                "concentration_ratio": concentration,
                "gini_coefficient": gini,
                "top_patients_count": top_n,
                "total_patients": total_beneficiaries,
                "threshold": THRESHOLDS["concentration_medium"]
            }
        })
        risk_score += 30
    
    # -----------------------------------------------------------------------
    # 2. Enrollment spike detection (sudden patient influx - kickback indicator)
    # -----------------------------------------------------------------------
    # This would require monthly enrollment data
    # For SQLite/PostgreSQL compatibility, we'll use strftime
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
    
    if len(monthly_new_beneficiaries) >= 3:
        counts = [record.new_count for record in monthly_new_beneficiaries]
        avg_monthly = sum(counts) / len(counts)
        std_monthly = np.std(counts) if len(counts) > 1 else 0
        
        spikes = []
        for record in monthly_new_beneficiaries:
            if record.new_count > avg_monthly * THRESHOLDS["spike_factor"]:
                z_score = (record.new_count - avg_monthly) / std_monthly if std_monthly > 0 else 0
                spikes.append({
                    "month": record.month,
                    "count": record.new_count,
                    "z_score": round(z_score, 2)
                })
        
        if spikes:
            evidence["enrollment_spikes"] = spikes
            findings.append({
                "type": "enrollment_spike",
                "severity": "high" if len(spikes) >= 2 else "medium",
                "description": f"Detected {len(spikes)} months with unusual enrollment spikes",
                "evidence": {
                    "spike_months": spikes,
                    "average_monthly_enrollment": round(avg_monthly, 1),
                    "std_deviation": round(std_monthly, 2)
                }
            })
            risk_score += 25 if len(spikes) >= 2 else 15
    
    # -----------------------------------------------------------------------
    # 3. Patient churn analysis (unusually loyal patients)
    # -----------------------------------------------------------------------
    long_term_patients = 0
    for stat in sorted_stats[:top_n]:
        if stat.first_claim and stat.last_claim:
            days_active = (stat.last_claim - stat.first_claim).days
            if days_active > 180:  # 6+ months
                long_term_patients += 1
    
    if long_term_patients > top_n * 0.8:  # >80% of top patients are long-term
        findings.append({
            "type": "patient_loyalty_anomaly",
            "severity": "medium",
            "description": f"Unusually high patient retention: {long_term_patients}/{top_n} top patients active >6 months",
            "evidence": {
                "long_term_patients": long_term_patients,
                "top_patients": top_n,
                "ratio": long_term_patients / top_n
            }
        })
        risk_score += 10
    
    # Normalize risk score to 0-100
    risk_score = min(100, risk_score)
    
    # Determine risk level
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Store kickback indicators if significant
    if risk_score >= 40:
        indicator = KickbackIndicator(
            provider_id=provider_id,
            beneficiary_concentration=concentration,
            cash_withdrawal_pattern=False,  # Requires external financial data
            referral_network={
                "top_patients": top_n,
                "concentration": concentration,
                "gini": float(gini) if 'gini' in locals() else 0
            },
            patient_enrollment_spikes=[s["month"] for s in spikes] if spikes else [],
            risk_score=risk_score,
            notes=f"Kickback risk score: {risk_score} - {risk_level}"
        )
        db.add(indicator)
        db.commit()
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "pattern_type": "kickback",
        "risk_score": risk_score,
        "risk_level": risk_level,
        "findings": findings,
        "evidence": evidence,
        "total_beneficiaries": total_beneficiaries,
        "analysis_period_days": lookback_days
    }


def comprehensive_pattern_analysis(
    db: Session,
    provider_id: int,
    lookback_days: int = 365,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Run comprehensive pattern-of-life analysis combining all detection methods.
    
    Args:
        db: Database session
        provider_id: Provider to analyze
        lookback_days: Days to look back
        use_cache: Whether to use cached POL results
        
    Returns:
        Comprehensive analysis with combined risk score
    """
    # Check cache if requested
    if use_cache:
        cached = db.query(POLResult).filter(
            and_(
                POLResult.provider_id == provider_id,
                POLResult.expires_at > datetime.utcnow()
            )
        ).first()
        
        if cached:
            logger.info(f"Returning cached POL result for provider {provider_id}")
            return {
                "provider_id": provider_id,
                "provider_name": cached.full_results.get("provider_name", "Unknown"),
                "provider_type": cached.full_results.get("provider_type"),
                "analysis_type": "comprehensive_pattern_of_life",
                "composite_risk_score": cached.risk_score,
                "severity": cached.risk_level,
                "analysis_modules": cached.full_results.get("analysis_modules", {}),
                "all_findings": cached.full_results.get("all_findings", []),
                "total_findings": len(cached.full_results.get("all_findings", [])),
                "analysis_period_days": lookback_days,
                "analysis_timestamp": cached.analyzed_at.isoformat(),
                "cached": True
            }
    
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}
    
    # Run all analysis modules
    behavioral = analyze_behavioral_patterns(db, provider_id, lookback_days)
    capacity = detect_capacity_violations(db, provider_id, lookback_days)
    kickback = detect_kickback_patterns(db, provider_id, lookback_days)
    
    # Extract risk scores with error handling
    behavioral_score = behavioral.get("risk_score", 0) if "error" not in behavioral else 0
    capacity_score = capacity.get("risk_score", 0) if "error" not in capacity else 0
    kickback_score = kickback.get("risk_score", 0) if "error" not in kickback else 0
    
    # Combine findings
    all_findings = []
    if "error" not in behavioral:
        all_findings.extend(behavioral.get("findings", []))
    if "error" not in capacity:
        all_findings.extend(capacity.get("findings", []))
    if "error" not in kickback:
        all_findings.extend(kickback.get("findings", []))
    
    # Calculate composite risk score (weighted average)
    composite_risk = (
        behavioral_score * WEIGHTS["behavioral"] +
        capacity_score * WEIGHTS["capacity"] +
        kickback_score * WEIGHTS["kickback"]
    )
    
    # Determine overall severity
    if composite_risk >= 70:
        severity = "HIGH"
    elif composite_risk >= 40:
        severity = "MEDIUM"
    else:
        severity = "LOW"
    
    # Prepare result
    result = {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "provider_type": provider.facility_type,
        "analysis_type": "comprehensive_pattern_of_life",
        "composite_risk_score": round(composite_risk, 1),
        "severity": severity,
        "analysis_modules": {
            "behavioral": {
                "risk_score": behavioral_score,
                "risk_level": behavioral.get("risk_level", "LOW"),
                "findings_count": len(behavioral.get("findings", []))
            },
            "capacity_violations": {
                "risk_score": capacity_score,
                "risk_level": capacity.get("risk_level", "LOW"),
                "findings_count": len(capacity.get("findings", []))
            },
            "kickback_indicators": {
                "risk_score": kickback_score,
                "risk_level": kickback.get("risk_level", "LOW"),
                "findings_count": len(kickback.get("findings", []))
            }
        },
        "all_findings": all_findings,
        "total_findings": len(all_findings),
        "analysis_period_days": lookback_days,
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "cached": False
    }
    
    # Cache the result
    if composite_risk > 0:
        # Check if existing cache entry
        existing = db.query(POLResult).filter(POLResult.provider_id == provider_id).first()
        
        if existing:
            existing.risk_score = int(composite_risk)
            existing.risk_level = severity
            existing.sudden_spike_score = kickback_score
            existing.capacity_exceed_score = capacity_score
            existing.full_results = result
            existing.analyzed_at = datetime.utcnow()
            existing.expires_at = datetime.utcnow() + timedelta(days=7)
        else:
            new_cache = POLResult(
                provider_id=provider_id,
                risk_score=int(composite_risk),
                risk_level=severity,
                sudden_spike_score=kickback_score,
                capacity_exceed_score=capacity_score,
                referral_concentration_score=kickback_score,
                full_results=result,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(new_cache)
        
        db.commit()
        logger.info(f"Cached POL result for provider {provider_id}")
    
    return result


def analyze_nyc_elderly_care_facilities(
    db: Session,
    min_risk_score: int = 50,
    limit: int = 100,
    include_details: bool = False
) -> Dict[str, Any]:
    """Analyze all NYC elderly care facilities for pattern-of-life anomalies.
    
    Focus on facility types relevant to recent prosecutions:
    - Nursing homes
    - Adult day care centers
    - Home health agencies
    - Rehabilitation facilities
    
    Args:
        db: Database session
        min_risk_score: Minimum risk score to include in results (0-100)
        limit: Maximum number of providers to analyze
        include_details: Whether to include full analysis details
        
    Returns:
        Analysis results for NYC elderly care facilities
    """
    # Target facility types from recent cases (case-insensitive matching)
    target_types = [
        "Nursing Home",
        "Adult Day Care",
        "Home Health Agency",
        "Skilled Nursing Facility",
        "Rehabilitation Facility",
        "Assisted Living",
        "Long Term Care"
    ]
    
    # Build NYC location filter
    nyc_boroughs = ["New York", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    location_filters = [Provider.city.ilike(f"%{borough}%") for borough in nyc_boroughs]
    
    # Build facility type filters
    type_filters = [Provider.facility_type.ilike(f"%{ft}%") for ft in target_types]
    
    # Query NYC providers of target types
    providers = (
        db.query(Provider)
        .filter(
            and_(
                Provider.state == "NY",
                or_(*location_filters),
                or_(*type_filters)
            )
        )
        .limit(limit)
        .all()
    )
    
    if not providers:
        return {
            "analysis_type": "nyc_elderly_care_sweep",
            "target_facility_types": target_types,
            "providers_analyzed": 0,
            "high_risk_facilities": 0,
            "results": [],
            "message": "No matching facilities found"
        }
    
    results = []
    high_risk_count = 0
    risk_distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    
    for provider in providers:
        # Check cache first for performance
        cached = db.query(POLResult).filter(
            and_(
                POLResult.provider_id == provider.id,
                POLResult.expires_at > datetime.utcnow()
            )
        ).first()
        
        if cached:
            risk_score = cached.risk_score
            severity = cached.risk_level
            findings_count = len(cached.full_results.get("all_findings", [])) if cached.full_results else 0
        else:
            # Run full analysis
            analysis = comprehensive_pattern_analysis(db, provider.id, use_cache=True)
            risk_score = analysis.get("composite_risk_score", 0)
            severity = analysis.get("severity", "LOW")
            findings_count = analysis.get("total_findings", 0)
        
        if risk_score >= min_risk_score:
            result = {
                "provider_id": provider.id,
                "npi": provider.npi,
                "name": provider.name,
                "city": provider.city,
                "facility_type": provider.facility_type,
                "risk_score": risk_score,
                "severity": severity,
                "findings_count": findings_count
            }
            
            if include_details and not cached:
                # Include full analysis (expensive)
                result["full_analysis"] = analysis
            
            results.append(result)
            
            if risk_score >= 70:
                high_risk_count += 1
                risk_distribution["HIGH"] += 1
            elif risk_score >= 40:
                risk_distribution["MEDIUM"] += 1
            else:
                risk_distribution["LOW"] += 1
    
    # Sort by risk score descending
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "analysis_type": "nyc_elderly_care_sweep",
        "target_facility_types": target_types,
        "providers_analyzed": len(providers),
        "high_risk_facilities": high_risk_count,
        "risk_distribution": risk_distribution,
        "results": results,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


def get_provider_risk_summary(
    db: Session,
    provider_id: int
) -> Dict[str, Any]:
    """Get quick risk summary for a provider (lightweight, cached).
    
    Args:
        db: Database session
        provider_id: Provider ID
        
    Returns:
            Quick risk summary
    """
    # Check cache
    cached = db.query(POLResult).filter(
        and_(
            POLResult.provider_id == provider_id,
            POLResult.expires_at > datetime.utcnow()
        )
    ).first()
    
    if cached:
        return {
            "provider_id": provider_id,
            "risk_score": cached.risk_score,
            "risk_level": cached.risk_level,
            "cached": True,
            "analyzed_at": cached.analyzed_at.isoformat()
        }
    
    # Run quick analysis (simplified)
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}
    
    # Get some quick indicators
    capacity_violations = db.query(CapacityViolation).filter(
        CapacityViolation.provider_id == provider_id
    ).count()
    
    kickback_indicators = db.query(KickbackIndicator).filter(
        KickbackIndicator.provider_id == provider_id
    ).first()
    
    # Simple risk calculation
    risk_score = 0
    if capacity_violations > 0:
        risk_score += min(40, capacity_violations * 5)
    if kickback_indicators and kickback_indicators.risk_score:
        risk_score += kickback_indicators.risk_score * 0.5
    
    risk_score = min(100, risk_score)
    
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "provider_id": provider_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "cached": False
    }
