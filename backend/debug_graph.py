
import logging
from analytics.graph_analyzer import FraudRingDetector
from database import SessionLocal

logging.basicConfig(level=logging.INFO)

try:
    db = SessionLocal()
    detector = FraudRingDetector(db)
    detector.build_provider_network()
    rings = detector.detect_fraud_rings()
    print("Fraud Rings Success!")
    
    insights = detector.generate_network_insights()
    print("Insights Success!")
    
    import json
    # Try to serialize to JSON to catch numpy type errors
    json.dumps(insights)
    print("JSON Serialization Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
