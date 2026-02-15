from sqlalchemy import text
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

class CDPAPDetector:
    """
    Consumer Directed Personal Assistance Program (CDPAP) Fraud Detector.
    Targets:
    1. "Relative Racket": Caregivers with only 1 patient (likely a relative) billing max hours.
    2. Impossible Hours: Billing > 16 hours/day (physically impossible to sustain).
    """

    def __init__(self, db: Session):
        self.db = db
        self.cdpap_codes = ('T1019',) # Personal care services, per 15 min

    def detect_suspicious_caregivers(self, max_patients: int = 1, min_hours_daily: float = 8.0) -> List[Dict]:
        """
        Identify caregivers who exclusively serve 1-2 patients and bill high hours.
        This often indicates a family member getting paid to 'care' for a relative without documentation.
        """
        # T1019 is 15-min unit. 4 units = 1 hour.
        # Daily threshold in units: 8 hours * 4 = 32 units.
        
        sql = text("""
            WITH cdpap_claims AS (
                SELECT 
                    provider_id,
                    beneficiary_id,
                    claim_date,
                    SUM(units) as daily_units
                FROM claims
                WHERE billing_code IN :codes
                GROUP BY provider_id, beneficiary_id, claim_date
            ),
            provider_stats AS (
                SELECT 
                    provider_id,
                    COUNT(DISTINCT beneficiary_id) as patient_count,
                    AVG(daily_units) as avg_daily_units,
                    MAX(daily_units) as max_daily_units
                FROM cdpap_claims
                GROUP BY provider_id
            )
            SELECT 
                p.id as provider_id,
                p.name as provider_name,
                s.patient_count,
                s.avg_daily_units / 4.0 as avg_daily_hours
            FROM provider_stats s
            JOIN providers p ON s.provider_id = p.id
            WHERE s.patient_count <= :max_patients
            AND (s.avg_daily_units / 4.0) >= :min_hours
            ORDER BY avg_daily_hours DESC
            LIMIT 50;
        """)
        
        results = self.db.execute(sql, {
            "codes": self.cdpap_codes,
            "max_patients": max_patients,
            "min_hours": min_hours_daily
        }).fetchall()
        
        return [dict(row._mapping) for row in results]

    def detect_overlapping_hours(self) -> List[Dict]:
        """
        Identify caregivers billing for multiple patients at the exact same time?
        (Hard without timestamps, but we can check if total daily hours > 24).
        """
        sql = text("""
            SELECT 
                c.provider_id,
                p.name as provider_name,
                c.claim_date,
                SUM(c.units) / 4.0 as total_hours_billed
            FROM claims c
            JOIN providers p ON c.provider_id = p.id
            WHERE c.billing_code IN :codes
            GROUP BY c.provider_id, p.name, c.claim_date
            HAVING SUM(c.units) / 4.0 > 24 -- Impossible to work > 24 hours/day
            ORDER BY total_hours_billed DESC
            LIMIT 20;
        """)
        
        results = self.db.execute(sql, {"codes": self.cdpap_codes}).fetchall()
        return [dict(row._mapping) for row in results]

    def get_caregiver_network(self, limit: int = 100) -> Dict:
        """
        Get network edges for CDPAP relationships (Caregiver -> Patient).
        Returns nodes and links for visualization.
        """
        sql = text("""
            SELECT 
                c.provider_id,
                p.name as provider_name,
                c.beneficiary_id,
                SUM(c.units) / 4.0 as total_hours
            FROM claims c
            JOIN providers p ON c.provider_id = p.id
            WHERE c.billing_code IN :codes
            GROUP BY c.provider_id, p.name, c.beneficiary_id
            HAVING SUM(c.units) > 100 -- Only significant relationships
            LIMIT :limit
        """)
        
        results = self.db.execute(sql, {"codes": self.cdpap_codes, "limit": limit}).fetchall()
        
        nodes = []
        links = []
        seen_nodes = set()
        
        for row in results:
            pid = str(row.provider_id)
            bid = f"B-{row.beneficiary_id}"
            
            if pid not in seen_nodes:
                nodes.append({"id": pid, "label": row.provider_name, "type": "Caregiver", "val": 10})
                seen_nodes.add(pid)
            
            if bid not in seen_nodes:
                nodes.append({"id": bid, "label": f"Patient {row.beneficiary_id}", "type": "Beneficiary", "val": 5})
                seen_nodes.add(bid)
                
            links.append({
                "source": pid,
                "target": bid,
                "value": float(row.total_hours)
            })
            
        return {"nodes": nodes, "links": links}
