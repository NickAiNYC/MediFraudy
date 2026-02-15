from sqlalchemy import text
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

class RecipientDetector:
    """
    Recipient Fraud Detector.
    Targets:
    1. Card Sharing: One beneficiary ID used in geographically distinct locations on the same day.
    2. Doctor Shopping: Visiting multiple providers of the same specialty in a short period (already covered elsewhere but good to have here).
    """

    def __init__(self, db: Session):
        self.db = db

    def detect_card_sharing(self, min_distance_miles: float = 50.0) -> List[Dict]:
        """
        Identify beneficiaries with claims in different cities on the same day.
        Using a simplified check: Different Cities on same day.
        """
        # Note: Ideally we calculate distance between zips. 
        # Here we just look for distinct cities on the same day for the same beneficiary.
        
        sql = text("""
            SELECT 
                c.beneficiary_id,
                c.claim_date,
                COUNT(DISTINCT p.city) as city_count,
                string_agg(DISTINCT p.city, ', ') as cities,
                string_agg(DISTINCT p.name, ', ') as providers
            FROM claims c
            JOIN providers p ON c.provider_id = p.id
            WHERE c.beneficiary_id IS NOT NULL
            GROUP BY c.beneficiary_id, c.claim_date
            HAVING COUNT(DISTINCT p.city) > 1
            ORDER BY city_count DESC
            LIMIT 50;
        """)
        
        results = self.db.execute(sql).fetchall()
        
        # In a real app, we would filter by actual distance between cities.
        # For now, we return the raw multi-city hits.
        return [dict(row._mapping) for row in results]

    def detect_medication_resale(self, min_pharmacies: int = 3) -> List[Dict]:
        """
        Identify beneficiaries engaging in 'Doctor Shopping' or Reselling.
        Criteria: Visiting multiple distinct providers for similar services/codes 
        in a short window, or hoarding high volumes.
        
        Simplified: Beneficiaries visiting > min_pharmacies distinct providers 
        in the last 30 days (simulated by looking at the whole dataset for now).
        """
        sql = text("""
            SELECT 
                c.beneficiary_id,
                COUNT(DISTINCT c.provider_id) as provider_count,
                COUNT(c.id) as claim_count,
                SUM(c.amount) as total_cost
            FROM claims c
            WHERE c.beneficiary_id IS NOT NULL
            GROUP BY c.beneficiary_id
            HAVING COUNT(DISTINCT c.provider_id) >= :min_pharmacies
            ORDER BY provider_count DESC
            LIMIT 50;
        """)
        
        results = self.db.execute(sql, {"min_pharmacies": min_pharmacies}).fetchall()
        return [dict(row._mapping) for row in results]
