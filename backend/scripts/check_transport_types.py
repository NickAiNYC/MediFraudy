
from database import SessionLocal
from models import Provider
from sqlalchemy import func

def check_provider_types():
    db = SessionLocal()
    try:
        # Check facility types
        types = db.query(Provider.facility_type, func.count(Provider.id))\
            .group_by(Provider.facility_type)\
            .order_by(func.count(Provider.id).desc())\
            .all()
        
        print("\n--- Facility Types ---")
        for t, c in types:
            if t and ('transport' in t.lower() or 'ambul' in t.lower() or 'taxi' in t.lower()):
                print(f"{t}: {c}")

        # Check specialties
        specs = db.query(Provider.specialty, func.count(Provider.id))\
            .group_by(Provider.specialty)\
            .order_by(func.count(Provider.id).desc())\
            .all()
            
        print("\n--- Specialties ---")
        for s, c in specs:
            if s and ('transport' in s.lower() or 'ambul' in s.lower() or 'taxi' in s.lower()):
                print(f"{s}: {c}")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_provider_types()
