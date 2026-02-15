from sqlalchemy import text
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

class PharmacyDetector:
    """
    Pharmacy Fraud Detector.
    Targets:
    1. Lidocaine Patch Dumping (High volume of high-margin topical pain patches)
    2. Polypharmacy Cocktails (Dangerous combinations like Opioid + Benzo + Muscle Relaxant)
    3. Pharmacy-Prescriber Rings (High correlation between a specific Dr. and a specific Pharmacy)
    """

    def __init__(self, db: Session):
        self.db = db
        # Lidocaine 5% Patches, Ointments, Compound Kits
        self.lidocaine_codes = ('A6250', 'A6260', 'J2001', 'Q4080', 'A6257') 

    def detect_lidocaine_dumping(self, threshold_amount: float = 5000.0) -> List[Dict]:
        """
        Identify providers prescribing excessive Lidocaine patches.
        This is a classic 'phantom pain' kickback scheme.
        """
        sql = text("""
            SELECT 
                p.id as provider_id,
                p.name as provider_name,
                COUNT(c.id) as script_count,
                SUM(c.amount) as total_cost,
                COUNT(DISTINCT c.beneficiary_id) as patient_count
            FROM claims c
            JOIN providers p ON c.provider_id = p.id
            WHERE c.billing_code IN :codes
            GROUP BY p.id, p.name
            HAVING SUM(c.amount) > :threshold
            ORDER BY total_cost DESC
            LIMIT 50;
        """)
        
        results = self.db.execute(sql, {
            "codes": self.lidocaine_codes,
            "threshold": threshold_amount
        }).fetchall()
        
        return [dict(row._mapping) for row in results]

    def detect_prescriber_pharmacy_collusion(self, min_shared_patients: int = 10) -> List[Dict]:
        """
        Identify strict steering: 
        Dr. X sends 90% of their scripts to Pharmacy Y.
        
        Logic: Find pairs of Providers (one Prescriber, one Pharmacy) 
        that share an unusually high number of unique patients.
        """
        sql = text("""
            WITH PatientTrips AS (
                SELECT beneficiary_id, provider_id, COUNT(*) as claim_count
                FROM claims
                GROUP BY beneficiary_id, provider_id
            ),
            SharedPatients AS (
                SELECT 
                    p1.provider_id as prescriber_id,
                    p2.provider_id as pharmacy_id,
                    COUNT(p1.beneficiary_id) as shared_patient_count
                FROM PatientTrips p1
                JOIN PatientTrips p2 ON p1.beneficiary_id = p2.beneficiary_id
                WHERE p1.provider_id != p2.provider_id
                GROUP BY p1.provider_id, p2.provider_id
                HAVING COUNT(p1.beneficiary_id) >= :min_shared
            )
            SELECT 
                sp.prescriber_id,
                pr.name as prescriber_name,
                sp.pharmacy_id,
                ph.name as pharmacy_name,
                sp.shared_patient_count
            FROM SharedPatients sp
            JOIN providers pr ON sp.prescriber_id = pr.id
            JOIN providers ph ON sp.pharmacy_id = ph.id
            WHERE pr.facility_type LIKE '%Physician%' OR pr.facility_type LIKE '%Clinic%'
            AND (ph.facility_type LIKE '%Pharmacy%' OR ph.name LIKE '%PHARMACY%')
            ORDER BY sp.shared_patient_count DESC
            LIMIT 20;
        """)
        
        results = self.db.execute(sql, {"min_shared": min_shared_patients}).fetchall()
        return [dict(row._mapping) for row in results]
