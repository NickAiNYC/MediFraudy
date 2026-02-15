
import pandas as pd
import numpy as np
from sqlalchemy import func, desc, text
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from models import Claim, Provider

logger = logging.getLogger(__name__)

class MemberProfiler:
    """
    Analyzes beneficiary behavior to detect fraud patterns such as:
    - Identity Theft (High-Cost Members)
    - Doctor Shopping (High Provider Count)
    - Pill Mills (Specific drug patterns)
    """

    def __init__(self, db: Session):
        self.db = db

    def detect_pill_mills(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Identify beneficiaries who are obtaining controlled substances 
        from multiple providers (doctor shopping).
        """
        # Controlled substance procedure codes (example list)
        controlled_codes = ('G0480', 'G0481', 'G0482', 'G0483', '80305', '80306', '80307')
        
        sql = text("""
            SELECT 
                beneficiary_id,
                COUNT(DISTINCT provider_id) as provider_count,
                COUNT(id) as script_count,
                SUM(amount) as total_spent
            FROM claims
            WHERE billing_code IN :codes
            GROUP BY beneficiary_id
            HAVING COUNT(DISTINCT provider_id) >= 3
            ORDER BY provider_count DESC
            LIMIT :limit
        """)
        
        results = self.db.execute(sql, {"codes": controlled_codes, "limit": limit}).fetchall()
        
        return [
            {
                "beneficiary_id": r[0],
                "provider_count": r[1],
                "script_count": r[2],
                "total_spent": float(r[3]),
                "risk_factor": "pill_mill_suspect",
                "details": f"Obtained scripts from {r[1]} different providers."
            }
            for r in results
        ]

    def get_member_stats(self) -> Dict[str, float]:
        """
        Aggregates claim statistics per beneficiary.
        Returns global population stats (mean, stddev).
        """
        # Calculate global stats in SQL first
        stats_query = text("""
            SELECT 
                AVG(total_cost) as avg_cost, STDDEV(total_cost) as std_cost,
                AVG(unique_providers) as avg_prov, STDDEV(unique_providers) as std_prov
            FROM (
                SELECT beneficiary_id, 
                       SUM(amount) as total_cost, 
                       COUNT(DISTINCT provider_id) as unique_providers
                FROM claims 
                GROUP BY beneficiary_id
            ) as sub
        """)
        
        result = self.db.execute(stats_query).fetchone()
        if not result or result[0] is None:
            logger.warning("Not enough data for member profiling")
            return {}
            
        self.global_stats = {
            "avg_cost": float(result[0] or 0),
            "std_cost": float(result[1] or 1),
            "avg_prov": float(result[2] or 0),
            "std_prov": float(result[3] or 1)
        }
        
        logger.info(f"Global Member Stats: {self.global_stats}")
        
        return self.global_stats

    def identify_high_risk_members(self, z_threshold: float = 3.0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Finds members exceeding Z-score threshold for cost or provider count.
        """
        if not hasattr(self, 'global_stats'):
            self.get_member_stats()
            
        avg_cost = self.global_stats["avg_cost"]
        std_cost = self.global_stats["std_cost"]
        
        # Identify High Cost Members via SQL
        # (cost - avg) / std > z  => cost > avg + z * std
        cost_cutoff = avg_cost + (z_threshold * std_cost)
        
        sql = text("""
            SELECT 
                beneficiary_id, 
                SUM(amount) as total_cost, 
                COUNT(id) as claim_count,
                COUNT(DISTINCT provider_id) as unique_providers
            FROM claims 
            GROUP BY beneficiary_id
            HAVING SUM(amount) > :cost_cutoff
            ORDER BY total_cost DESC
            LIMIT :limit
        """)
        
        results = self.db.execute(sql, {"cost_cutoff": cost_cutoff, "limit": limit}).fetchall()
        
        high_risk_members = []
        for r in results:
            z_score = (float(r[1]) - avg_cost) / std_cost
            high_risk_members.append({
                "beneficiary_id": r[0],
                "total_cost": float(r[1]),
                "claim_count": int(r[2]),
                "unique_providers": int(r[3]),
                "risk_factor": "high_cost",
                "z_score": round(z_score, 2),
                "details": f"Total spend is {z_score:.1f} standard deviations above mean"
            })
            
        return high_risk_members

    def identify_doctor_shoppers(self, z_threshold: float = 3.0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Finds members visiting an unusually high number of unique providers.
        """
        if not hasattr(self, 'global_stats'):
            self.get_member_stats()
            
        avg_prov = self.global_stats["avg_prov"]
        std_prov = self.global_stats["std_prov"]
        
        prov_cutoff = avg_prov + (z_threshold * std_prov)
        
        sql = text("""
            SELECT 
                beneficiary_id, 
                SUM(amount) as total_cost, 
                COUNT(id) as claim_count,
                COUNT(DISTINCT provider_id) as unique_providers
            FROM claims 
            GROUP BY beneficiary_id
            HAVING COUNT(DISTINCT provider_id) > :prov_cutoff
            ORDER BY unique_providers DESC
            LIMIT :limit
        """)
        
        results = self.db.execute(sql, {"prov_cutoff": prov_cutoff, "limit": limit}).fetchall()
        
        shoppers = []
        for r in results:
            z_score = (float(r[3]) - avg_prov) / std_prov
            shoppers.append({
                "beneficiary_id": r[0],
                "total_cost": float(r[1]),
                "claim_count": int(r[2]),
                "unique_providers": int(r[3]),
                "risk_factor": "doctor_shopping",
                "z_score": round(z_score, 2),
                "details": f"Visited {r[3]} unique providers ({z_score:.1f} SD above mean)"
            })
            
        return shoppers

    def identify_pill_mill_patients(self, drug_codes: List[str], threshold: float = 3.0) -> List[Dict[str, Any]]:
        """
        Identify patients receiving extreme quantities of controlled substances.
        """
        if not drug_codes:
            # Default to common opioid codes if none provided (Placeholders)
            drug_codes = ["J2270", "J2274", "J2278"] 
            
        sql = text("""
            SELECT 
                beneficiary_id, 
                COUNT(*) as prescription_count, 
                SUM(amount) as total_cost, 
                COUNT(DISTINCT provider_id) as provider_count 
            FROM claims 
            WHERE billing_code IN :drug_codes 
            GROUP BY beneficiary_id 
            HAVING COUNT(*) > (SELECT AVG(cnt) + :threshold * STDDEV(cnt) 
                              FROM (SELECT COUNT(*) as cnt 
                                    FROM claims 
                                    WHERE billing_code IN :drug_codes 
                                    GROUP BY beneficiary_id) as sub) 
        """)
        
        # SQLAlchemy handles list/tuple binding for IN clauses differently based on driver
        # For psycopg2, tuple usually works.
        results = self.db.execute(sql, {"drug_codes": tuple(drug_codes), "threshold": threshold}).fetchall()
        
        suspects = []
        for r in results:
             suspects.append({
                "beneficiary_id": r[0],
                "prescription_count": int(r[1]),
                "total_cost": float(r[2]),
                "provider_count": int(r[3]),
                "risk_factor": "pill_mill_beneficiary",
                "details": f"Received {r[1]} prescriptions from {r[3]} providers"
            })
            
        return suspects
