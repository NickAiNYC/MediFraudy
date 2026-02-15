"""
Peer Group Profiling (Optum FADS Style).

Providers are compared against their 'peers' (same specialty, region, size).
Metrics are normalized using Z-scores or Percentiles.

Key Metrics:
1. Average Cost per Patient
2. Claims per Day
3. Procedure Code Mix (e.g., % of high-level E&M codes)
4. Denial Rate (if available)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, text
import pandas as pd
import numpy as np
from models import Provider, Claim, PeerGroup, POLResult

class PeerProfiler:
    def __init__(self, db: Session):
        self.db = db

    def create_peer_groups(self):
        """
        Automatically group providers based on available metadata.
        For now, we group by (specialty, state).
        """
        # Fetch distinct combinations
        groups = self.db.query(
            Provider.specialty, Provider.state
        ).distinct().all()
        
        for specialty, state in groups:
            if not specialty or not state:
                continue
                
            group_name = f"{specialty} - {state}"
            existing = self.db.query(PeerGroup).filter_by(name=group_name).first()
            
            if not existing:
                pg = PeerGroup(
                    name=group_name,
                    specialty=specialty,
                    geographic_region=state
                )
                self.db.add(pg)
        
        self.db.commit()

    def calculate_baselines(self):
        """
        Calculate statistical baselines for each peer group.
        Updates the 'baselines' JSON field in PeerGroup table.
        """
        groups = self.db.query(PeerGroup).all()
        
        for group in groups:
            # Get providers in this group
            providers = self.db.query(Provider.id).filter(
                Provider.specialty == group.specialty,
                Provider.state == group.geographic_region
            ).all()
            
            provider_ids = [p.id for p in providers]
            
            if not provider_ids:
                continue
                
            # Calculate metrics for these providers
            # Example Metric: Average Cost per Claim
            sql = text("""
                SELECT provider_id, AVG(amount) as avg_cost
                FROM claims
                WHERE provider_id IN :p_ids
                GROUP BY provider_id
            """)
            
            # Using pandas for easy stats
            df = pd.read_sql(sql, self.db.bind, params={"p_ids": tuple(provider_ids)})
            
            if df.empty:
                continue
                
            mean_cost = df['avg_cost'].mean()
            std_cost = df['avg_cost'].std()
            
            # Store baselines
            group.baselines = {
                "avg_cost_mean": float(mean_cost),
                "avg_cost_std": float(std_cost) if not np.isnan(std_cost) else 0.0,
                "provider_count": len(provider_ids)
            }
            
            self.db.add(group)
            
        self.db.commit()

    def identify_outliers(self, threshold_z=3.0):
        """
        Identify providers who deviate significantly from their peer group baseline.
        """
        groups = self.db.query(PeerGroup).all()
        outliers = []
        
        for group in groups:
            if not group.baselines:
                continue
                
            mean = group.baselines.get("avg_cost_mean", 0)
            std = group.baselines.get("avg_cost_std", 1)
            
            if std == 0:
                continue
            
            # Find providers with Z-score > threshold
            # Query again (inefficient but clear for now)
            providers = self.db.query(Provider.id).filter(
                Provider.specialty == group.specialty,
                Provider.state == group.geographic_region
            ).all()
            provider_ids = tuple([p.id for p in providers])
            
            sql = text("""
                SELECT provider_id, AVG(amount) as avg_cost
                FROM claims
                WHERE provider_id IN :p_ids
                GROUP BY provider_id
                HAVING (AVG(amount) - :mean) / :std > :threshold
            """)
            
            result = self.db.execute(sql, {
                "p_ids": provider_ids,
                "mean": mean,
                "std": std,
                "threshold": threshold_z
            }).fetchall()
            
            for row in result:
                outliers.append({
                    "provider_id": row.provider_id,
                    "metric": "avg_cost",
                    "value": row.avg_cost,
                    "z_score": (row.avg_cost - mean) / std,
                    "peer_group": group.name
                })
                
        return outliers
