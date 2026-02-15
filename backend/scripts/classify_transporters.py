
import logging
from sqlalchemy import func, case, update, text
from database import SessionLocal
from models import Provider, Claim

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of HCPCS codes associated with transportation
TRANSPORT_CODES = [
    'A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0430', 'A0431', 'A0432',
    'A0433', 'A0434', 'A0435', 'A0436', 'A0888', 'A0998', 'A0999',
    'T2001', 'T2002', 'T2003', 'T2004', 'T2005', 'T2007',
    'T2049', 'S0215', 'S0209'
]

def classify_transporters():
    session = SessionLocal()
    try:
        logger.info("Starting granular transporter classification...")
        
        # Define categories with associated HCPCS codes
        # Ordered from general/lower-acuity to specific/higher-acuity
        # so that if a provider does multiple, they get the higher classification (last one wins)
        categories = { 
            'Other Transport': ['A0888', 'A0998', 'A0999', 'S0209'],       # Miscellaneous 
            'Taxi/Livery': ['T2005', 'T2007', 'T2049'],                   # Non-emergency 
            'Wheelchair Van': ['T2001', 'T2002', 'T2003', 'T2004'],       # Wheelchair 
            'Ambulette': ['A0430', 'A0431', 'A0432', 'A0433', 'A0434'],  # Stretcher 
            'Ambulance': ['A0425', 'A0426', 'A0427', 'A0428', 'A0429'],  # ALS/BLS 
        } 
        
        for category, codes in categories.items():
            logger.info(f"Classifying {category} providers...")
            codes_str = ", ".join([f"'{c}'" for c in codes])
            
            # Update providers who have billed these codes
            # We also set facility_type to 'Transportation' for all of them
            sql = text(f""" 
            UPDATE providers 
            SET specialty = :category, facility_type = 'Transportation'
            WHERE id IN ( 
                SELECT provider_id 
                FROM claims 
                WHERE billing_code IN ({codes_str}) 
                GROUP BY provider_id 
            ); 
            """) 
            
            result = session.execute(sql, {"category": category})
            session.commit()
            logger.info(f"Updated {result.rowcount} providers to {category}")

    except Exception as e:
        logger.error(f"Error during classification: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    classify_transporters()
