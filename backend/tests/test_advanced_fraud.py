import unittest
from unittest.mock import MagicMock, patch
from analytics.sadc_detector import SADCDetector
from analytics.pharmacy_detector import PharmacyDetector

from analytics.cdpap_detector import CDPAPDetector

class TestAdvancedFraud(unittest.TestCase):
    
    def test_cdpap_suspicious_caregivers(self):
        mock_db = MagicMock()
        
        mock_row = MagicMock()
        mock_row._mapping = {
            "provider_id": 303,
            "provider_name": "Caregiver Alice",
            "patient_count": 1,
            "avg_daily_hours": 12.0
        }
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        detector = CDPAPDetector(mock_db)
        results = detector.detect_suspicious_caregivers()
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['provider_name'], "Caregiver Alice")
        
        args, kwargs = mock_db.execute.call_args
        params = args[1]
        self.assertIn("T1019", str(params['codes']))

    def test_sadc_attendance_spikes(self):
        # Mock DB setup
        mock_db = MagicMock()
        
        # Mock result for attendance spikes
        # Expected: provider_id, provider_name, claim_date, daily_census, avg_census, z_score
        mock_row = MagicMock()
        mock_row._mapping = {
            "provider_id": 101,
            "provider_name": "Shady SADC",
            "claim_date": "2024-01-01",
            "daily_census": 100,
            "avg_census": 20,
            "z_score": 4.5
        }
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        detector = SADCDetector(mock_db)
        results = detector.detect_attendance_spikes()
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['provider_name'], "Shady SADC")
        self.assertGreater(results[0]['z_score'], 3)
        
        # Verify SQL execution
        mock_db.execute.assert_called_once()
        args, kwargs = mock_db.execute.call_args
        self.assertIn("WITH daily_counts AS", str(args[0]))

    @patch('analytics.sadc_detector.get_db_direct')
    def test_sadc_ghost_patients(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_row = MagicMock()
        mock_row._mapping = {"beneficiary_id": 555, "other_medical_claims": 0}
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        detector = SADCDetector()
        results = detector.detect_ghost_patients()
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['beneficiary_id'], 555)

    def test_pharmacy_lidocaine_dumping(self):
        # Mock DB setup
        mock_db = MagicMock()
        
        # Mock result for lidocaine dumping
        mock_row = MagicMock()
        mock_row._mapping = {
            "provider_id": 202,
            "provider_name": "Dr. Feelgood",
            "total_lidocaine_cost": 15000.0,
            "claim_count": 50
        }
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        detector = PharmacyDetector(mock_db)
        results = detector.detect_lidocaine_dumping(threshold_amount=5000.0)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['provider_name'], "Dr. Feelgood")
        self.assertGreater(results[0]['total_lidocaine_cost'], 5000)

if __name__ == '__main__':
    unittest.main()
