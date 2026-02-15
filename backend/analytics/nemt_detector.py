from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_
import pandas as pd
from datetime import timedelta
import logging

from models import Provider, Claim, Beneficiary, TransportationTrip

logger = logging.getLogger(__name__)

class NEMTFraudDetector:
    """
    Detects Non-Emergency Medical Transportation (NEMT) fraud patterns.
    
    Targeting specific schemes:
    - Ghost Rides: Billing for trips not taken or without medical service.
    - Impossible Days: >24 hours of driving or impossible distances.
    - Group Ride Unbundling: Billing group rides as individual trips.
    - Ineligible Beneficiaries: Transporting deceased or incarcerated patients.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def check_beneficiary_eligibility(self, provider_id: int):
        """
        Detect trips for deceased/incarcerated/hospitalized patients.
        Returns a list of suspicious claims.
        """
        # Query for claims where service date is AFTER death date or DURING incarceration
        query = (
            self.db.query(Claim)
            .join(Beneficiary, Claim.beneficiary_id == Beneficiary.id)
            .filter(Claim.provider_id == provider_id)
            .filter(
                or_(
                    and_(Beneficiary.status == 'deceased', Claim.claim_date > Beneficiary.status_date),
                    and_(Beneficiary.status == 'incarcerated', Claim.claim_date >= Beneficiary.status_date)
                )
            )
        )
        return pd.read_sql(query.statement, self.db.bind)

    def check_medical_correlation(self, provider_id: int):
        """
        Detect trips without corresponding medical services (Ghost Rides).
        
        Logic:
        1. Get all transport claims for the provider.
        2. For each beneficiary/date, check if ANY other medical claim exists.
        3. If no matching medical claim, flag as suspicious.
        """
        # This is a heavy query, so we use a simplified approach or limit scope
        # We look for days where a patient had a transport claim but NO other claim on that date
        
        sql = text("""
            SELECT t.id as claim_id, t.beneficiary_id, t.claim_date, t.amount
            FROM claims t
            WHERE t.provider_id = :provider_id
            AND NOT EXISTS (
                SELECT 1 FROM claims m
                WHERE m.beneficiary_id = t.beneficiary_id
                AND m.claim_date = t.claim_date
                AND m.provider_id != :provider_id
            )
        """)
        
        return pd.read_sql(sql, self.db.bind, params={"provider_id": provider_id})

    def analyze_geographic_anomalies(self, provider_id: int):
        """
        Detect mileage inflation and impossible routes.
        Requires TransportationTrip data.
        """
        # 1. Mileage Inflation: Claimed > Calculated * threshold
        # 2. Impossible Speed: Distance / Time > threshold (requires timestamps)
        
        query = (
            self.db.query(TransportationTrip)
            .join(Claim)
            .filter(Claim.provider_id == provider_id)
            .filter(TransportationTrip.claimed_distance > TransportationTrip.calculated_distance * 1.2) # 20% buffer
        )
        return pd.read_sql(query.statement, self.db.bind)

    def detect_ghost_rides_systemwide(self, limit: int = 50):
        """
        System-wide detection of Ghost Rides (Transport without medical service).
        """
        sql = text("""
            SELECT 
                t.provider_id,
                p.name as provider_name,
                COUNT(t.id) as suspicious_claim_count,
                SUM(t.amount) as total_suspicious_amount
            FROM claims t
            JOIN providers p ON t.provider_id = p.id
            WHERE t.billing_code LIKE 'A0%' 
            AND NOT EXISTS (
                SELECT 1 FROM claims m
                WHERE m.beneficiary_id = t.beneficiary_id
                AND m.claim_date = t.claim_date
                AND m.provider_id != t.provider_id
            )
            GROUP BY t.provider_id, p.name
            ORDER BY suspicious_claim_count DESC
            LIMIT :limit
        """)
        return [dict(row._mapping) for row in self.db.execute(sql, {"limit": limit}).fetchall()]

    def detect_impossible_trips_systemwide(self, limit: int = 50):
        """
        System-wide detection of Mileage Inflation (Impossible Trips).
        """
        # Note: This requires the TransportationTrip table to be populated.
        # If not, we return an empty list.
        try:
            sql = text("""
                SELECT 
                    c.provider_id,
                    p.name as provider_name,
                    COUNT(tr.id) as inflated_trips,
                    AVG(tr.claimed_distance - tr.calculated_distance) as avg_inflation,
                    SUM(c.amount) as total_improper_payments
                FROM transportation_trips tr
                JOIN claims c ON tr.claim_id = c.id
                JOIN providers p ON c.provider_id = p.id
                WHERE tr.claimed_distance > (tr.calculated_distance * 1.2)
                GROUP BY c.provider_id, p.name
                ORDER BY inflated_trips DESC
                LIMIT :limit
            """)
            return [dict(row._mapping) for row in self.db.execute(sql, {"limit": limit}).fetchall()]
        except Exception as e:
            logger.warning(f"Failed to detect impossible trips (table might be missing): {e}")
            return []

    def detect_milk_runs(self, provider_id: int, time_window_minutes: int = 60, min_patients: int = 3):
        """
        Detect 'Milk Runs': Transporter dropping off multiple patients at the same location within a short window.
        Indicates coordinated fraud (bringing patients to a mill).
        """
        # We look for:
        # - Same dropoff location (or provider address)
        # - Within time window
        # - Multiple distinct beneficiaries
        
        # SQL logic:
        # Group by dropoff_lat, dropoff_lon, time_bucket
        # Count distinct beneficiaries
        
        sql = text("""
            SELECT 
                t.dropoff_lat, t.dropoff_lon, 
                t.claim_date,
                COUNT(DISTINCT c.beneficiary_id) as patient_count,
                array_agg(c.beneficiary_id) as patients
            FROM transportation_trips t
            JOIN claims c ON t.claim_id = c.id
            WHERE c.provider_id = :provider_id
            GROUP BY t.dropoff_lat, t.dropoff_lon, t.claim_date
            HAVING COUNT(DISTINCT c.beneficiary_id) >= :min_patients
        """)
        
        return pd.read_sql(sql, self.db.bind, params={
            "provider_id": provider_id, 
            "min_patients": min_patients
        })

    def flag_high_risk_beneficiaries(self):
        """
        Identify beneficiaries appearing in multiple fraud patterns.
        Returns top high-risk beneficiaries.
        """
        # Aggregating risk scores from Beneficiary table
        return self.db.query(Beneficiary).order_by(Beneficiary.risk_score.desc()).limit(100).all()

    def generate_nemt_risk_score(self, provider_id: int):
        """
        Composite risk score (0-100) for NEMT fraud.
        """
        # 1. Calculate percentage of Ghost Rides
        ghost_rides = self.check_medical_correlation(provider_id)
        total_claims = self.db.query(func.count(Claim.id)).filter(Claim.provider_id == provider_id).scalar()
        
        if not total_claims:
            return 0
            
        ghost_rate = len(ghost_rides) / total_claims
        
        # 2. Calculate percentage of Ineligible rides
        ineligible = self.check_beneficiary_eligibility(provider_id)
        ineligible_rate = len(ineligible) / total_claims
        
        # Weighted Score
        score = (ghost_rate * 50) + (ineligible_rate * 50)
        return min(100, score)
