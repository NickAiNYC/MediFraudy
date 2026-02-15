from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from analytics.sadc_detector import SADCDetector
from analytics.cdpap_detector import CDPAPDetector
from analytics.pharmacy_detector import PharmacyDetector
from analytics.recipient_detector import RecipientDetector
from analytics.nemt_detector import NEMTFraudDetector

class DashboardAggregator:
    def __init__(self, db: Session):
        self.sadc = SADCDetector(db)
        self.cdpap = CDPAPDetector(db)
        self.pharmacy = PharmacyDetector(db)
        self.recipient = RecipientDetector(db)
        self.nemt = NEMTFraudDetector(db) 

    def get_summary_stats(self) -> Dict:
        """
        Get high-level statistics for the dashboard.
        """
        # This is a bit expensive, in production we'd cache this or use pre-calculated tables.
        # For the demo, we'll run the lightweight queries.
        
        sadc_spikes = self.sadc.detect_attendance_spikes(threshold_z=3.0)
        cdpap_suspicious = self.cdpap.detect_suspicious_caregivers()
        lidocaine_dumpers = self.pharmacy.detect_lidocaine_dumping()
        card_sharers = self.recipient.detect_card_sharing()
        ghost_rides = self.nemt.detect_ghost_rides_systemwide()
        
        # Calculate a simple risk score for top providers
        risk_scores = {}
        
        # SADC Risk: 20 points per spike event
        for row in sadc_spikes:
            pid = row['provider_id']
            name = row['provider_name']
            if pid not in risk_scores:
                risk_scores[pid] = {'name': name, 'score': 0, 'vectors': []}
            risk_scores[pid]['score'] += 20
            if 'SADC' not in risk_scores[pid]['vectors']:
                risk_scores[pid]['vectors'].append('SADC')

        # CDPAP Risk: 10 points * (avg_daily_hours - 8)
        for row in cdpap_suspicious:
            pid = row['provider_id']
            name = row['provider_name']
            if pid not in risk_scores:
                risk_scores[pid] = {'name': name, 'score': 0, 'vectors': []}
            hours_over = max(0, row['avg_daily_hours'] - 8)
            risk_scores[pid]['score'] += int(hours_over * 10)
            if 'CDPAP' not in risk_scores[pid]['vectors']:
                risk_scores[pid]['vectors'].append('CDPAP')

        # Pharmacy Risk: 1 point per $100 of Lidocaine
        for row in lidocaine_dumpers:
            pid = row['provider_id']
            name = row['provider_name']
            if pid not in risk_scores:
                risk_scores[pid] = {'name': name, 'score': 0, 'vectors': []}
            points = int(row['total_cost'] / 100)
            risk_scores[pid]['score'] += points
            if 'Pharmacy' not in risk_scores[pid]['vectors']:
                risk_scores[pid]['vectors'].append('Pharmacy')

        # NEMT Risk: 10 points per ghost ride
        for row in ghost_rides:
            pid = row['provider_id']
            name = row['provider_name']
            if pid not in risk_scores:
                risk_scores[pid] = {'name': name, 'score': 0, 'vectors': []}
            risk_scores[pid]['score'] += (row['suspicious_claim_count'] * 10)
            if 'NEMT' not in risk_scores[pid]['vectors']:
                risk_scores[pid]['vectors'].append('NEMT')

        # Sort by score
        top_risks = sorted(risk_scores.values(), key=lambda x: x['score'], reverse=True)[:10]
        
        return {
            "top_risks": top_risks,
            "sadc_count": len(sadc_spikes),
            "cdpap_count": len(cdpap_suspicious),
            "pharmacy_count": len(lidocaine_dumpers),
            "recipient_count": len(card_sharers),
            "nemt_count": len(ghost_rides)
        }
