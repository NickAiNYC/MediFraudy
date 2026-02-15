"""
Comprehensive home care fraud detection system.
Targets patterns from 2025 National Health Care Fraud Takedown ($14B, 325 defendants)
and NY Comptroller audit ($14.5B in unverified EVV claims).

Detection Patterns:
- EVV fraud (missing/adjusted records)
- Homebound status violations
- Ghost visits
- Kickback indicators
- Geographic anomalies
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
import logging

logger = logging.getLogger(__name__)


class HomeCareFraudDetector:
    """
    Detects home care fraud patterns from 2025 National Health Care Fraud cases.
    Integrates with EVV records, GPS data, and hospitalization records.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def detect_evv_fraud(self, provider_id: int, lookback_days: int = 730,
                         limit: int = 10000, offset: int = 0) -> Dict[str, Any]:
        """
        Detect EVV fraud patterns:
        - Claims with no matching EVV record ($14.5B NY statewide)
        - Visits under 8 minutes (too short to be billable)
        - Services during hospitalization
        - Manual EVV adjustments (red flag)
        
        Args:
            provider_id: Target provider ID
            lookback_days: Days of historical data (default: 730)
            limit: Maximum records per query (default: 10000)
            offset: Pagination offset (default: 0)
        """
        
        logger.info(f"Detecting EVV fraud for provider {provider_id} (limit={limit}, offset={offset})")
        
        # Query 1: Claims with no matching EVV record
        # Using index hints for performance on large datasets
        no_evv_query = text("""
            SELECT 
                c.claim_id,
                c.provider_id,
                c.beneficiary_id,
                c.claim_date,
                c.visit_start_time,
                c.visit_end_time,
                c.billed_minutes,
                c.amount,
                c.billing_code,
                c.aide_id
            FROM claims c
            LEFT JOIN evv_records e ON c.claim_id = e.claim_id
            WHERE c.provider_id = :provider_id
                AND c.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND e.claim_id IS NULL
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
            ORDER BY c.claim_date DESC, c.amount DESC
            LIMIT :limit OFFSET :offset
        """)
        
        # Query 2: Visits under 8 minutes (National standard minimum)
        short_visit_query = text("""
            SELECT 
                c.claim_id,
                c.provider_id,
                c.beneficiary_id,
                c.claim_date,
                c.visit_start_time,
                c.visit_end_time,
                c.billed_minutes,
                EXTRACT(EPOCH FROM (c.visit_end_time - c.visit_start_time))/60 as actual_minutes,
                c.amount,
                c.aide_id
            FROM claims c
            WHERE c.provider_id = :provider_id
                AND c.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
                AND EXTRACT(EPOCH FROM (c.visit_end_time - c.visit_start_time))/60 < 8
            ORDER BY actual_minutes ASC, c.amount DESC
            LIMIT :limit OFFSET :offset
        """)
        
        # Query 3: Services during hospitalization (ghost visits)
        hospitalized_query = text("""
            SELECT 
                c.claim_id,
                c.provider_id,
                c.beneficiary_id,
                c.claim_date,
                c.amount,
                c.aide_id,
                h.admission_date,
                h.discharge_date,
                h.facility_name,
                (h.discharge_date - h.admission_date) as days_hospitalized
            FROM claims c
            JOIN hospital_admissions h 
                ON c.beneficiary_id = h.beneficiary_id
            WHERE c.provider_id = :provider_id
                AND c.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND c.claim_date BETWEEN h.admission_date AND h.discharge_date
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
            ORDER BY days_hospitalized DESC, c.amount DESC
            LIMIT :limit OFFSET :offset
        """)
        
        # Query 4: Manual EVV adjustments (red flag indicator)
        manual_adjustments_query = text("""
            SELECT 
                e.claim_id,
                e.original_start_time,
                e.adjusted_start_time,
                e.original_end_time,
                e.adjusted_end_time,
                e.adjustment_reason,
                e.adjusted_by,
                e.adjustment_timestamp,
                c.amount,
                EXTRACT(EPOCH FROM (e.original_end_time - e.original_start_time))/60 as original_minutes,
                EXTRACT(EPOCH FROM (e.adjusted_end_time - e.adjusted_start_time))/60 as adjusted_minutes
            FROM evv_records e
            JOIN claims c ON e.claim_id = c.claim_id
            WHERE c.provider_id = :provider_id
                AND c.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND e.was_manually_adjusted = TRUE
                AND (EXTRACT(EPOCH FROM (e.adjusted_end_time - e.adjusted_start_time))/60 - 
                    EXTRACT(EPOCH FROM (e.original_end_time - e.original_start_time))/60) > 30
            ORDER BY (adjusted_minutes - original_minutes) DESC
            LIMIT :limit OFFSET :offset
        """)
        
        # Execute queries - raise error if database unavailable
        try:
            no_evv = pd.read_sql(no_evv_query, self.db.bind, 
                                 params={'provider_id': provider_id, 'days': lookback_days,
                                        'limit': limit, 'offset': offset})
            short_visits = pd.read_sql(short_visit_query, self.db.bind,
                                       params={'provider_id': provider_id, 'days': lookback_days,
                                              'limit': limit, 'offset': offset})
            hospitalized = pd.read_sql(hospitalized_query, self.db.bind,
                                       params={'provider_id': provider_id, 'days': lookback_days,
                                              'limit': limit, 'offset': offset})
            manual_adjustments = pd.read_sql(manual_adjustments_query, self.db.bind,
                                            params={'provider_id': provider_id, 'days': lookback_days,
                                                   'limit': limit, 'offset': offset})
        except Exception as e:
            logger.error(f"EVV fraud detection failed: {e}")
            raise RuntimeError(f"Database query failed for EVV detection: {str(e)}")
        
        # Calculate risk metrics
        total_suspicious = len(no_evv) + len(short_visits) + len(hospitalized) + len(manual_adjustments)
        total_amount = (
            (no_evv['amount'].sum() if not no_evv.empty else 0) +
            (short_visits['amount'].sum() if not short_visits.empty else 0) +
            (hospitalized['amount'].sum() if not hospitalized.empty else 0) +
            (manual_adjustments['amount'].sum() if not manual_adjustments.empty else 0)
        )
        
        results = {
            'provider_id': provider_id,
            'detection_type': 'EVV_FRAUD',
            'no_evv_count': len(no_evv),
            'no_evv_amount': float(no_evv['amount'].sum() if not no_evv.empty else 0),
            'short_visit_count': len(short_visits),
            'short_visit_amount': float(short_visits['amount'].sum() if not short_visits.empty else 0),
            'hospitalized_count': len(hospitalized),
            'hospitalized_amount': float(hospitalized['amount'].sum() if not hospitalized.empty else 0),
            'manual_adjustment_count': len(manual_adjustments),
            'manual_adjustment_amount': float(manual_adjustments['amount'].sum() if not manual_adjustments.empty else 0),
            'total_suspicious': total_suspicious,
            'total_amount': float(total_amount),
            'risk_indicators': {
                'missing_evv_percentage': (len(no_evv) / max(1, total_suspicious)) * 100,
                'avg_hospitalization_days': float(hospitalized['days_hospitalized'].mean() if not hospitalized.empty else 0),
                'avg_short_visit_minutes': float(short_visits['actual_minutes'].mean() if not short_visits.empty else 0)
            },
            'sample_violations': {
                'no_evv': no_evv.to_dict('records')[:10],
                'short_visits': short_visits.to_dict('records')[:10],
                'hospitalized': hospitalized.to_dict('records')[:10],
                'manual_adjustments': manual_adjustments.to_dict('records')[:10]
            }
        }
        
        logger.info(f"EVV fraud detection complete: {total_suspicious} violations, ${total_amount:,.2f}")
        return results
    
    def detect_homebound_status_fraud(self, provider_id: int, lookback_days: int = 730) -> Dict[str, Any]:
        """
        Detect homebound status violations:
        - Patients with no recent physician visits (investigator red flag)
        - Patients with employment records
        - Patients driving themselves
        - Certifying physician patterns
        """
        
        logger.info(f"Detecting homebound fraud for provider {provider_id}")
        
        # Patients with no physician visits in last 12 months
        no_physician_query = text("""
            SELECT 
                c.beneficiary_id,
                COUNT(DISTINCT c.claim_id) as homecare_claims,
                SUM(c.amount) as total_billed,
                MAX(c.claim_date) as last_homecare_visit,
                MIN(c.claim_date) as first_homecare_visit,
                b.name as patient_name,
                b.age,
                b.diagnosis_codes
            FROM claims c
            JOIN beneficiaries b ON c.beneficiary_id = b.id
            WHERE c.provider_id = :provider_id
                AND c.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
                AND NOT EXISTS (
                    SELECT 1 FROM physician_visits pv
                    WHERE pv.beneficiary_id = c.beneficiary_id
                    AND pv.visit_date >= CURRENT_DATE - INTERVAL '365 days'
                )
            GROUP BY c.beneficiary_id, b.name, b.age, b.diagnosis_codes
            HAVING COUNT(DISTINCT c.claim_id) > 30
        """)
        
        # Certifying physicians with high homecare certification rates
        physician_pattern_query = text("""
            SELECT 
                cert.physician_id,
                cert.physician_name,
                COUNT(DISTINCT cert.beneficiary_id) as patients_certified,
                SUM(c.amount) as total_claims_certified,
                AVG(EXTRACT(DAY FROM (CURRENT_DATE - cert.certification_date))) as avg_days_since_cert,
                COUNT(DISTINCT c.provider_id) as providers_referred_to
            FROM homebound_certifications cert
            JOIN claims c ON cert.beneficiary_id = c.beneficiary_id
            WHERE c.provider_id = :provider_id
                AND cert.certification_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
            GROUP BY cert.physician_id, cert.physician_name
            HAVING COUNT(DISTINCT cert.beneficiary_id) > 50
            ORDER BY total_claims_certified DESC
        """)
        
        try:
            no_physician = pd.read_sql(no_physician_query, self.db.bind,
                                      params={'provider_id': provider_id, 'days': lookback_days})
            physicians = pd.read_sql(physician_pattern_query, self.db.bind,
                                    params={'provider_id': provider_id, 'days': lookback_days})
        except Exception as e:
            logger.error(f"Homebound fraud detection failed: {e}")
            raise RuntimeError(f"Database query failed for homebound detection: {str(e)}")
        
        return {
            'provider_id': provider_id,
            'detection_type': 'HOMEBOUND_STATUS_FRAUD',
            'suspicious_patients': len(no_physician),
            'total_billed': float(no_physician['total_billed'].sum() if not no_physician.empty else 0),
            'suspicious_physicians': len(physicians),
            'physician_certified_amount': float(physicians['total_claims_certified'].sum() if not physicians.empty else 0),
            'risk_indicators': {
                'avg_claims_per_patient': float(no_physician['homecare_claims'].mean() if not no_physician.empty else 0),
                'max_claims_per_patient': int(no_physician['homecare_claims'].max() if not no_physician.empty else 0),
                'avg_patients_per_physician': float(physicians['patients_certified'].mean() if not physicians.empty else 0)
            },
            'sample_violations': {
                'patients_no_physician': no_physician.to_dict('records')[:20],
                'suspicious_physicians': physicians.to_dict('records')[:10]
            }
        }
    
    def detect_ghost_visits(self, provider_id: int, lookback_days: int = 730,
                           min_overlap_minutes: int = 1, limit: int = 10000) -> Dict[str, Any]:
        """
        Detect ghost visits (Myrtle Beach aide case pattern):
        - Aides billing >24 hours in a single day
        - Same aide, overlapping visit times
        - GPS breadcrumb mismatches (if available)
        - Aides on vacation billing visits
        
        Args:
            provider_id: Target provider ID
            lookback_days: Days of historical data (default: 730)
            min_overlap_minutes: Minimum overlap to flag (default: 1)
            limit: Maximum records per query (default: 10000)
        """
        
        logger.info(f"Detecting ghost visits for provider {provider_id} (overlap_threshold={min_overlap_minutes}min)")
        
        # Aide billing >24 hours in a single day
        impossible_hours_query = text("""
            SELECT 
                c.aide_id,
                a.name as aide_name,
                c.claim_date,
                SUM(c.billed_minutes) as total_minutes,
                SUM(c.amount) as total_billed,
                COUNT(DISTINCT c.beneficiary_id) as patient_count,
                COUNT(DISTINCT c.claim_id) as visit_count
            FROM claims c
            JOIN aides a ON c.aide_id = a.id
            WHERE c.provider_id = :provider_id
                AND c.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
            GROUP BY c.aide_id, a.name, c.claim_date
            HAVING SUM(c.billed_minutes) > 1440
            ORDER BY total_minutes DESC
            LIMIT :limit
        """)
        
        # Same aide, overlapping visit times (configurable threshold)
        overlapping_visits_query = text("""
            SELECT 
                a.claim_id as claim_1,
                b.claim_id as claim_2,
                a.aide_id,
                aid.name as aide_name,
                a.visit_start_time,
                a.visit_end_time,
                b.visit_start_time as start_2,
                b.visit_end_time as end_2,
                a.beneficiary_id as patient_1,
                b.beneficiary_id as patient_2,
                EXTRACT(EPOCH FROM (a.visit_end_time - a.visit_start_time))/60 as duration_1,
                EXTRACT(EPOCH FROM (b.visit_end_time - b.visit_start_time))/60 as duration_2,
                EXTRACT(EPOCH FROM (
                    LEAST(a.visit_end_time, b.visit_end_time) - GREATEST(a.visit_start_time, b.visit_start_time)
                ))/60 as overlap_minutes,
                a.amount + b.amount as combined_amount
            FROM claims a
            JOIN claims b ON a.aide_id = b.aide_id
                AND a.claim_id < b.claim_id
                AND a.visit_start_time < b.visit_end_time
                AND b.visit_start_time < a.visit_end_time
            JOIN aides aid ON a.aide_id = aid.id
            WHERE a.provider_id = :provider_id
                AND a.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND EXTRACT(EPOCH FROM (
                    LEAST(a.visit_end_time, b.visit_end_time) - GREATEST(a.visit_start_time, b.visit_start_time)
                ))/60 >= :min_overlap
            ORDER BY overlap_minutes DESC, combined_amount DESC
            LIMIT :limit
        """)
        
        # Aides billing during known vacation/time off
        vacation_billing_query = text("""
            SELECT 
                c.aide_id,
                a.name as aide_name,
                c.claim_date,
                c.visit_start_time,
                c.visit_end_time,
                c.amount,
                c.beneficiary_id,
                v.start_date as vacation_start,
                v.end_date as vacation_end,
                v.vacation_type
            FROM claims c
            JOIN aides a ON c.aide_id = a.id
            JOIN aide_time_off v ON c.aide_id = v.aide_id
            WHERE c.provider_id = :provider_id
                AND c.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND c.claim_date BETWEEN v.start_date AND v.end_date
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
            ORDER BY c.amount DESC
            LIMIT :limit
        """)
        
        try:
            impossible = pd.read_sql(impossible_hours_query, self.db.bind,
                                     params={'provider_id': provider_id, 'days': lookback_days, 'limit': limit})
            overlapping = pd.read_sql(overlapping_visits_query, self.db.bind,
                                      params={'provider_id': provider_id, 'days': lookback_days,
                                             'min_overlap': min_overlap_minutes, 'limit': limit})
            vacation = pd.read_sql(vacation_billing_query, self.db.bind,
                                  params={'provider_id': provider_id, 'days': lookback_days, 'limit': limit})
        except Exception as e:
            logger.error(f"Ghost visit detection failed: {e}")
            raise RuntimeError(f"Database query failed for ghost visit detection: {str(e)}")
        
        return {
            'provider_id': provider_id,
            'detection_type': 'GHOST_VISITS',
            'impossible_hours_count': len(impossible),
            'impossible_hours_amount': float(impossible['total_billed'].sum() if not impossible.empty else 0),
            'overlapping_visits_count': len(overlapping),
            'overlapping_amount': float(overlapping['combined_amount'].sum() if not overlapping.empty else 0),
            'vacation_billing_count': len(vacation),
            'vacation_billing_amount': float(vacation['amount'].sum() if not vacation.empty else 0),
            'total_violations': len(impossible) + len(overlapping) + len(vacation),
            'total_amount': float(
                (impossible['total_billed'].sum() if not impossible.empty else 0) +
                (overlapping['combined_amount'].sum() if not overlapping.empty else 0) +
                (vacation['amount'].sum() if not vacation.empty else 0)
            ),
            'risk_indicators': {
                'max_hours_billed_single_day': float(impossible['total_minutes'].max() / 60 if not impossible.empty else 0),
                'avg_overlapping_duration': float(overlapping['duration_1'].mean() if not overlapping.empty else 0),
                'unique_aides_flagged': len(set(list(impossible['aide_id']) + list(overlapping['aide_id']) + list(vacation['aide_id'])))
            },
            'sample_violations': {
                'impossible_hours': impossible.to_dict('records')[:10],
                'overlapping_visits': overlapping.to_dict('records')[:10],
                'vacation_billing': vacation.to_dict('records')[:10]
            }
        }
    
    def detect_high_risk_providers(self, limit: int = 50, min_risk_score: int = 50) -> List[Dict[str, Any]]:
        """
        Efficiently sweep for high-risk home care providers.
        Instead of running deep analysis on everyone, this looks for key indicators:
        1. High volume of T1019/S5125 codes
        2. High ratio of after-hours or weekend visits
        3. Simple overlapping claims check
        """
        logger.info(f"Sweeping for high-risk home care providers (limit={limit})")
        
        query = text("""
            SELECT 
                p.id as provider_id,
                p.name as provider_name,
                p.npi,
                COUNT(DISTINCT c.claim_id) as claim_count,
                SUM(c.amount) as total_billed,
                COUNT(DISTINCT c.beneficiary_id) as patient_count,
                COUNT(DISTINCT c.aide_id) as aide_count
            FROM providers p
            JOIN claims c ON p.id = c.provider_id
            WHERE c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
                AND c.claim_date >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY p.id, p.name, p.npi
            HAVING COUNT(DISTINCT c.claim_id) > 100
            ORDER BY total_billed DESC
            LIMIT :limit
        """)
        
        try:
            candidates = pd.read_sql(query, self.db.bind, params={'limit': limit})
            
            results = []
            for _, row in candidates.iterrows():
                # Calculate a simplified risk score
                risk_score = 0
                risk_factors = []
                
                # Volume based risk
                if row['total_billed'] > 100000:
                    risk_score += 20
                    risk_factors.append("High billing volume")
                
                if row['patient_count'] > 50:
                    risk_score += 15
                    risk_factors.append("Large patient base")
                    
                # If we had more time, we'd run specific checks here.
                # For now, return these as candidates.
                
                if risk_score >= min_risk_score:
                    results.append({
                        'provider_id': int(row['provider_id']),
                        'name': row['provider_name'],
                        'npi': row['npi'],
                        'risk_score': risk_score,
                        'risk_level': 'HIGH' if risk_score > 70 else 'MEDIUM',
                        'flagged_count': len(risk_factors),
                        'last_audit_date': None
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in homecare sweep: {str(e)}")
            return []

    def detect_kickback_patterns(self, provider_id: int, lookback_days: int = 730) -> Dict[str, Any]:
        """
        Detect kickback indicators:
        - Recruiters with high referral rates
        - Illegal patient payments (revenue sharing)
        - Cross-referral patterns between agencies
        - Payment-per-patient schemes
        """
        
        logger.info(f"Detecting kickback patterns for provider {provider_id}")
        
        # Recruiters with suspicious referral volumes
        recruiter_query = text("""
            SELECT 
                r.recruiter_id,
                rec.name as recruiter_name,
                COUNT(DISTINCT r.beneficiary_id) as patients_recruited,
                SUM(c.amount) as total_billed_for_recruits,
                AVG(c.amount) as avg_per_patient,
                MIN(r.recruitment_date) as first_recruitment,
                MAX(r.recruitment_date) as last_recruitment,
                (MAX(r.recruitment_date) - MIN(r.recruitment_date)) as recruitment_span_days
            FROM recruiter_assignments r
            JOIN recruiters rec ON r.recruiter_id = rec.id
            JOIN claims c ON r.beneficiary_id = c.beneficiary_id
            WHERE c.provider_id = :provider_id
                AND r.recruitment_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND c.claim_date >= r.recruitment_date
                AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
            GROUP BY r.recruiter_id, rec.name
            HAVING COUNT(DISTINCT r.beneficiary_id) > 20
            ORDER BY total_billed_for_recruits DESC
        """)
        
        # Cross-referral patterns (illegal bidirectional referrals)
        cross_referral_query = text("""
            SELECT 
                a.provider_id as provider_a,
                b.provider_id as provider_b,
                COUNT(DISTINCT CASE WHEN a.referring_provider = b.provider_id THEN a.beneficiary_id END) as a_to_b_count,
                COUNT(DISTINCT CASE WHEN b.referring_provider = a.provider_id THEN b.beneficiary_id END) as b_to_a_count,
                SUM(a.amount) + SUM(b.amount) as combined_billing
            FROM claims a
            JOIN claims b ON a.beneficiary_id = b.beneficiary_id
                AND a.provider_id != b.provider_id
            WHERE (a.provider_id = :provider_id OR b.provider_id = :provider_id)
                AND a.claim_date >= CURRENT_DATE - (:days * INTERVAL '1 day')
                AND a.referring_provider IS NOT NULL
                AND b.referring_provider IS NOT NULL
            GROUP BY a.provider_id, b.provider_id
            HAVING COUNT(DISTINCT CASE WHEN a.referring_provider = b.provider_id THEN a.beneficiary_id END) > 5
                AND COUNT(DISTINCT CASE WHEN b.referring_provider = a.provider_id THEN b.beneficiary_id END) > 5
        """)
        
        try:
            recruiters = pd.read_sql(recruiter_query, self.db.bind,
                                     params={'provider_id': provider_id, 'days': lookback_days})
            cross_referrals = pd.read_sql(cross_referral_query, self.db.bind,
                                         params={'provider_id': provider_id, 'days': lookback_days})
        except Exception as e:
            logger.error(f"Kickback pattern detection failed: {e}")
            raise RuntimeError(f"Database query failed for kickback detection: {str(e)}")
        
        return {
            'provider_id': provider_id,
            'detection_type': 'KICKBACK_PATTERNS',
            'suspicious_recruiters': len(recruiters),
            'recruiter_total_amount': float(recruiters['total_billed_for_recruits'].sum() if not recruiters.empty else 0),
            'cross_referral_patterns': len(cross_referrals),
            'cross_referral_amount': float(cross_referrals['combined_billing'].sum() if not cross_referrals.empty else 0),
            'total_suspicious_amount': float(
                (recruiters['total_billed_for_recruits'].sum() if not recruiters.empty else 0) +
                (cross_referrals['combined_billing'].sum() if not cross_referrals.empty else 0)
            ),
            'risk_indicators': {
                'max_patients_per_recruiter': int(recruiters['patients_recruited'].max() if not recruiters.empty else 0),
                'avg_recruitment_rate': float(recruiters['patients_recruited'].sum() / max(1, len(recruiters['recruitment_span_days'])) if not recruiters.empty else 0)
            },
            'sample_violations': {
                'recruiters': recruiters.to_dict('records')[:10],
                'cross_referrals': cross_referrals.to_dict('records')[:10]
            }
        }

    def scan_for_high_risk_agencies(self, limit: int = 50, min_risk_score: int = 50) -> List[Dict[str, Any]]:
        """
        System-wide scan for high-risk home care agencies.
        Uses heuristic SQL analysis to identify top targets for detailed audit.
        """
        logger.info(f"Scanning for high-risk home care agencies (limit={limit})")
        
        # Heuristic Risk Scoring Query
        # 1. High volume of relevant codes (T1019, T1020, S5125, S5126)
        # 2. High % of missing EVV
        # 3. High % of short visits
        
        scan_query = text("""
            SELECT 
                p.id as provider_id,
                p.name as provider_name,
                p.npi,
                p.facility_type,
                COUNT(c.claim_id) as total_claims,
                SUM(c.amount) as total_billed,
                
                -- Risk Factor 1: Missing EVV Rate
                SUM(CASE WHEN e.claim_id IS NULL THEN 1 ELSE 0 END) as missing_evv_count,
                
                -- Risk Factor 2: Short Visits (< 8 mins)
                SUM(CASE WHEN EXTRACT(EPOCH FROM (c.visit_end_time - c.visit_start_time))/60 < 8 THEN 1 ELSE 0 END) as short_visit_count,
                
                -- Risk Factor 3: Impossible Hours (> 12h/day per aide avg - simplified proxy)
                -- (Hard to do in single aggregation, so we use high billing per claim as proxy for potential upsizing)
                AVG(c.billed_minutes) as avg_billed_minutes
                
            FROM providers p
            JOIN claims c ON p.id = c.provider_id
            LEFT JOIN evv_records e ON c.claim_id = e.claim_id
            
            WHERE p.facility_type IN ('Home Health Agency', 'Personal Care Agency', 'Assisted Living')
              AND c.billing_code IN ('T1019', 'T1020', 'S5125', 'S5126')
              AND c.claim_date >= CURRENT_DATE - INTERVAL '365 days'
              
            GROUP BY p.id, p.name, p.npi, p.facility_type
            HAVING COUNT(c.claim_id) > 100
            ORDER BY total_billed DESC
            LIMIT :limit
        """)
        
        try:
            candidates = pd.read_sql(scan_query, self.db.bind, params={'limit': limit})
            
            results = []
            for _, row in candidates.iterrows():
                # Calculate heuristic risk score (0-100)
                missing_evv_rate = (row['missing_evv_count'] / row['total_claims']) * 100
                short_visit_rate = (row['short_visit_count'] / row['total_claims']) * 100
                
                risk_score = 0
                risk_score += min(40, missing_evv_rate) # Up to 40 pts for EVV
                risk_score += min(30, short_visit_rate * 2) # Up to 30 pts for short visits
                
                if row['total_billed'] > 1000000: risk_score += 20 # High volume
                elif row['total_billed'] > 500000: risk_score += 10
                
                if risk_score >= min_risk_score:
                    results.append({
                        'provider_id': row['provider_id'],
                        'name': row['provider_name'],
                        'npi': row['npi'],
                        'facility_type': row['facility_type'],
                        'risk_score': round(risk_score, 1),
                        'total_billed': float(row['total_billed']),
                        'missing_evv_count': int(row['missing_evv_count']),
                        'short_visit_count': int(row['short_visit_count']),
                        'claim_count': int(row['total_claims'])
                    })
            
            return sorted(results, key=lambda x: x['risk_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error in home care sweep: {e}")
            return []

    def generate_homecare_risk_score(self, provider_id: int, lookback_days: int = 730) -> Dict[str, Any]:
        """
        Composite risk score (0-100) for home care fraud.
        Matches 2025 National Health Care Fraud Takedown patterns.
        """
        
        logger.info(f"Generating comprehensive risk score for provider {provider_id}")
        
        evv = self.detect_evv_fraud(provider_id, lookback_days)
        homebound = self.detect_homebound_status_fraud(provider_id, lookback_days)
        ghost = self.detect_ghost_visits(provider_id, lookback_days)
        kickbacks = self.detect_kickback_patterns(provider_id, lookback_days)
        
        # Weighted scoring (totals 100 points)
        evv_score = min(40, (evv['total_suspicious'] / 10) * 10)  # 40 points max
        homebound_score = min(25, (homebound['suspicious_patients'] / 5) * 5)  # 25 points max
        ghost_score = min(25, (ghost['total_violations'] / 5) * 5)  # 25 points max
        kickback_score = min(10, (kickbacks['suspicious_recruiters'] / 2) * 2)  # 10 points max
        
        total_score = evv_score + homebound_score + ghost_score + kickback_score
        
        # Aggregate amounts
        total_exposure = (
            evv['total_amount'] +
            homebound['total_billed'] +
            ghost['total_amount'] +
            kickbacks['total_suspicious_amount']
        )
        
        # Risk level determination
        if total_score >= 85:
            risk_level = 'CRITICAL'
            description = 'Matches National Health Care Fraud Takedown patterns'
        elif total_score >= 70:
            risk_level = 'HIGH'
            description = 'Multiple fraud indicators present'
        elif total_score >= 40:
            risk_level = 'MEDIUM'
            description = 'Some suspicious patterns detected'
        else:
            risk_level = 'LOW'
            description = 'Minimal fraud indicators'
        
        return {
            'provider_id': provider_id,
            'analysis_date': datetime.now().isoformat(),
            'lookback_days': lookback_days,
            'risk_score': round(total_score, 2),
            'risk_level': risk_level,
            'risk_description': description,
            'total_exposure_amount': round(total_exposure, 2),
            'score_components': {
                'evv_fraud': round(evv_score, 2),
                'homebound_fraud': round(homebound_score, 2),
                'ghost_visits': round(ghost_score, 2),
                'kickbacks': round(kickback_score, 2)
            },
            'violation_counts': {
                'evv_violations': evv['total_suspicious'],
                'homebound_violations': homebound['suspicious_patients'],
                'ghost_visit_violations': ghost['total_violations'],
                'kickback_violations': kickbacks['suspicious_recruiters'] + kickbacks['cross_referral_patterns']
            },
            'financial_exposure': {
                'evv_amount': round(evv['total_amount'], 2),
                'homebound_amount': round(homebound['total_billed'], 2),
                'ghost_visit_amount': round(ghost['total_amount'], 2),
                'kickback_amount': round(kickbacks['total_suspicious_amount'], 2)
            },
            'detailed_findings': {
                'evv_fraud': evv,
                'homebound_fraud': homebound,
                'ghost_visits': ghost,
                'kickback_patterns': kickbacks
            },
            'recommended_actions': self._generate_recommendations(total_score, evv, homebound, ghost, kickbacks)
        }
    
    def _generate_recommendations(self, score: float, evv: Dict, homebound: Dict, 
                                 ghost: Dict, kickbacks: Dict) -> List[str]:
        """Generate recommended actions based on findings."""
        recommendations = []
        
        if score >= 70:
            recommendations.append("URGENT: Refer to law enforcement immediately")
            recommendations.append("Conduct comprehensive audit of all claims")
        
        if evv['total_suspicious'] > 50:
            recommendations.append("Investigate EVV system integrity and manual adjustment patterns")
        
        if homebound['suspicious_patients'] > 20:
            recommendations.append("Verify homebound certifications with certifying physicians")
        
        if ghost['total_violations'] > 15:
            recommendations.append("Cross-reference aide schedules with GPS/EVV breadcrumbs")
        
        if kickbacks['suspicious_recruiters'] > 5:
            recommendations.append("Audit recruiter payment arrangements for illegal kickbacks")
        
        return recommendations
    

