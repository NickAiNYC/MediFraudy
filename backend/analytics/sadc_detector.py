import pandas as pd
from sqlalchemy import text
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from datetime import datetime, timedelta

class SADCDetector:
    """
    Social Adult Day Care (SADC) Fraud Detector.
    Targets:
    1. Mass Attendance (Improbable daily capacity utilization)
    2. "Payday" Spikes (Attendance correlates with kickback cycles)
    3. Low-Acuity Recruitment (Patients with no medical history attending daily)
    """

    def __init__(self, db: Session):
        self.db = db
        # Common NY SADC Codes: S5100, S5101, S5102, S5105
        self.sadc_codes = ('S5100', 'S5101', 'S5102', 'S5105', 'T1020') 

    def detect_attendance_spikes(self, threshold_z: float = 2.5) -> List[Dict]:
        """
        Identify SADC facilities with suspicious attendance spikes 
        (e.g., 200 people showing up on a Friday vs 50 on Monday).
        """
        sql = text("""
            WITH daily_counts AS (
                SELECT 
                    provider_id, 
                    claim_date, 
                    COUNT(DISTINCT beneficiary_id) as daily_census
                FROM claims 
                WHERE billing_code IN :sadc_codes
                GROUP BY provider_id, claim_date
            ),
            stats AS (
                SELECT 
                    provider_id,
                    AVG(daily_census) as avg_census,
                    STDDEV(daily_census) as std_census
                FROM daily_counts
                GROUP BY provider_id
            )
            SELECT 
                d.provider_id,
                p.name as provider_name,
                d.claim_date,
                d.daily_census,
                s.avg_census,
                (d.daily_census - s.avg_census) / NULLIF(s.std_census, 0) as z_score
            FROM daily_counts d
            JOIN stats s ON d.provider_id = s.provider_id
            JOIN providers p ON d.provider_id = p.id
            WHERE (d.daily_census - s.avg_census) > (:threshold * s.std_census)
            AND d.daily_census > 20  -- Ignore small facilities
            ORDER BY z_score DESC
            LIMIT 50;
        """)
        
        results = self.db.execute(sql, {
            "sadc_codes": self.sadc_codes, 
            "threshold": threshold_z
        }).fetchall()
        
        return [dict(row._mapping) for row in results]

    def detect_impossible_attendance(self) -> List[Dict]:
        """
        Identify beneficiaries who attend SADC 6-7 days a week consistently.
        Realistically, frail elderly patients cannot attend daily without fatigue.
        """
        sql = text("""
            SELECT 
                c.provider_id,
                p.name as provider_name,
                c.beneficiary_id,
                COUNT(DISTINCT c.claim_date) as attendance_days,
                MIN(c.claim_date) as first_visit,
                MAX(c.claim_date) as last_visit
            FROM claims c
            JOIN providers p ON c.provider_id = p.id
            WHERE c.billing_code IN :sadc_codes
            GROUP BY c.provider_id, p.name, c.beneficiary_id
            HAVING COUNT(DISTINCT c.claim_date) > 24 -- More than 24 days in a month (assuming monthly batch)
            ORDER BY attendance_days DESC
            LIMIT 100;
        """)
        
        results = self.db.execute(sql, {"sadc_codes": self.sadc_codes}).fetchall()
        return [dict(row._mapping) for row in results]

    def detect_ghost_patients(self) -> List[Dict]:
        """
        Identify 'Ghost' SADC patients: 
        High SADC attendance but ZERO other medical claims (doctors, pharmacy, hospital).
        Implies they are healthy individuals recruited just for the SADC kickback.
        """
        sql = text("""
            WITH sadc_patients AS (
                SELECT DISTINCT beneficiary_id 
                FROM claims 
                WHERE billing_code IN :sadc_codes
            ),
            medical_claims AS (
                SELECT 
                    beneficiary_id, 
                    COUNT(*) as med_count 
                FROM claims 
                WHERE billing_code NOT IN :sadc_codes
                GROUP BY beneficiary_id
            )
            SELECT 
                s.beneficiary_id,
                COALESCE(m.med_count, 0) as other_medical_claims
            FROM sadc_patients s
            LEFT JOIN medical_claims m ON s.beneficiary_id = m.beneficiary_id
            WHERE COALESCE(m.med_count, 0) < 3 -- Very low medical usage for "frail" elderly
            LIMIT 50;
        """)
        
        results = self.db.execute(sql, {"sadc_codes": self.sadc_codes}).fetchall()
        return [dict(row._mapping) for row in results]

    def get_daily_attendance_heatmap(self, limit: int = 1000, days_back: int = 90) -> List[Dict]:
        """
        Get daily attendance counts for SADC providers to visualize 'Payday' patterns.
        Returns: { date: '2024-01-01', provider_id: 123, count: 50 }
        """
        # Calculate cutoff date
        min_date = datetime.now().date() - timedelta(days=days_back)
        
        sql = text("""
            SELECT 
                claim_date,
                provider_id,
                COUNT(DISTINCT beneficiary_id) as value
            FROM claims
            WHERE billing_code IN :sadc_codes
            AND claim_date >= :min_date
            GROUP BY claim_date, provider_id
            HAVING COUNT(DISTINCT beneficiary_id) > 10
            ORDER BY claim_date DESC
            LIMIT :limit
        """)
        
        results = self.db.execute(sql, {
            "sadc_codes": self.sadc_codes, 
            "limit": limit,
            "min_date": min_date
        }).fetchall()
        return [dict(row._mapping) for row in results]
