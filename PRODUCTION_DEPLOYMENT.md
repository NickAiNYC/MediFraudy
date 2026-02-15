# 🚀 PRODUCTION DEPLOYMENT - Connect to Real DOJ 77M Claims Data

## Status Check

Your system has:
- ✅ 77.3M real claims in PostgreSQL
- ✅ 318,794 real providers  
- ✅ All fraud detectors written and compiled
- ❌ Mock data fallbacks still active in detectors
- ❌ API endpoints returning demo responses

## IMMEDIATE ACTION REQUIRED

The detectors have try/except blocks that fall back to mock data when queries fail. This must be removed completely for production.

---

## STEP 1: Remove All Mock Data Generators

### Identify Mock Data in Detectors

All detectors have `_generate_mock_*` methods that must be removed:

```bash
# Find all mock generators
grep -r "_generate_mock" backend/analytics/*.py
grep -r "except.*return.*mock" backend/analytics/*.py
```

### Files to Clean

1. `backend/analytics/sadc_detector.py`
2. `backend/analytics/cdpap_detector.py`
3. `backend/analytics/nemt_detector.py`
4. `backend/analytics/pharmacy_detector.py`
5. `backend/analytics/recipient_detector.py`
6. `backend/analytics/patterns.py`

---

## STEP 2: Update Each Detector

### Pattern: Replace Mock Fallbacks with Real Queries

**BEFORE (Mock Fallback):**
```python
try:
    results = db.query(Claims).filter(...).all()
except Exception as e:
    logger.warning(f"Query failed, using mock: {e}")
    return self._generate_mock_sadc_data()  # ❌ REMOVE THIS
```

**AFTER (Production Ready):**
```python
try:
    results = db.query(Claims).filter(...).all()
except Exception as e:
    logger.error(f"CRITICAL: Database query failed: {e}")
    raise  # ✅ Let error propagate to API
```

---

## STEP 3: Verify Database Connection

Create `backend/scripts/verify_production.py`:

```python
#!/usr/bin/env python
"""Verify production data is live and accessible."""

import os
from sqlalchemy import create_engine, text
from config import settings

def verify():
    print("🔍 VERIFYING PRODUCTION DATA...")
    print(f"Database: {settings.database_dsn.split('@')[-1]}")
    
    try:
        engine = create_engine(settings.database_dsn, echo=False)
        with engine.connect() as conn:
            # Check claims
            result = conn.execute(text("SELECT COUNT(*) FROM claims"))
            claims = result.scalar()
            print(f"✅ Claims: {claims:,}")
            
            if claims < 70_000_000:
                print("❌ ERROR: Expected 77M+ claims")
                return False
            
            # Check providers
            result = conn.execute(text("SELECT COUNT(*) FROM providers"))
            providers = result.scalar()
            print(f"✅ Providers: {providers:,}")
            
            # Sample real fraud
            result = conn.execute(text("""
                SELECT COUNT(*), AVG(amount) 
                FROM claims 
                WHERE amount > 100000
            """))
            high_value = result.fetchone()
            print(f"✅ High-value claims (>$100K): {high_value[0]:,}")
            
            print("\n✅ PRODUCTION DATA VERIFIED")
            return True
            
    except Exception as e:
        print(f"❌ VERIFICATION FAILED: {e}")
        return False

if __name__ == "__main__":
    verify()
```

Run it:
```bash
cd backend
python scripts/verify_production.py
```

---

## STEP 4: Update API Endpoints

### File: `backend/routes/analytics_trigger.py`

Update each endpoint to query REAL data:

```python
@router.get("/api/analytics/sadc/attendance-heatmap")
def get_sadc_heatmap(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Real SADC heatmap from 77M claims."""
    detector = SADCDetector(db)
    
    try:
        # Query REAL database - no mock fallback
        results = detector.detect_attendance_anomalies()
        
        if not results:
            logger.warning(f"No SADC anomalies found (may be normal)")
            return []
        
        return results[:limit]
        
    except Exception as e:
        logger.error(f"SADC query failed: {e}")
        raise  # ✅ Return 500, don't hide error
```

### Update All Endpoints

Replace all mock interceptors with real DB queries:

```python
# ❌ REMOVE THIS PATTERN:
except Exception:
    return MockDataGenerator.sadc_data()

# ✅ REPLACE WITH THIS:
except Exception as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

---

## STEP 5: Update Frontend to Handle Real Data

### File: `frontend/src/services/api.ts`

Ensure NO mock interceptors:

```typescript
// ❌ REMOVE if exists:
if (process.env.REACT_APP_MODE === 'DEMO') {
    return mockData.sadc_heatmap;
}

// ✅ KEEP ONLY REAL API CALLS:
const response = await fetch('http://localhost:8000/api/analytics/sadc/attendance-heatmap');
const data = await response.json();
return data;
```

---

## STEP 6: Update Environment Variables

Create `.env` in project root:

```bash
# Production Mode
ENVIRONMENT=production
DEBUG=false

# Real Database
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/medicaid_db

# Data Source
MEDICAID_DATASET_PATH=/path/to/77M_claims.parquet

# Feature Flags
ENABLE_POL_CACHE=true
POL_CACHE_DAYS=7

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_MODE=production
```

---

## STEP 7: Remove Demo Mode Completely

Search and remove all demo/mock flags:

```bash
# Find all demo references
grep -r "DEMO\|mock\|synthetic" backend/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx"

# Remove them
sed -i '' '/DEMO_MODE/d' backend/main.py
sed -i '' '/if.*mock/d' backend/routes/*.py
```

---

## STEP 8: Deploy Production

### Option A: Docker Production Build

```bash
# Build production image
docker build -f backend/Dockerfile.prod -t medicaid-backend:prod backend/

# Run with real DB
docker run -d \
  --name medicaid_backend_prod \
  -e DATABASE_URL="postgresql://postgres:pass@db:5432/medicaid_db" \
  -e ENVIRONMENT=production \
  -p 8000:8000 \
  medicaid-backend:prod
```

### Option B: Direct Python (Development)

```bash
cd backend

# Export production settings
export ENVIRONMENT=production
export DATABASE_URL="postgresql://postgres:password@localhost:5432/medicaid_db"
export DEBUG=false

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# In another terminal, start frontend
cd ../frontend
npm run build
npm start
```

---

## STEP 9: Verify Production Live

### Check Backend is Using Real Data

```bash
# Test API with real data
curl http://localhost:8000/api/analytics/sadc/attendance-heatmap?limit=1 | jq

# Should return REAL facility names, not "Provider 12345"

# Check database connection
curl http://localhost:8000/api/providers?limit=1 | jq '.providers[0].name'

# Should show real provider like "ABC HOME CARE, INC."
```

### Check Dashboard Shows Real Data

1. Open http://localhost:3000
2. Go to **Fraud Rings** tab
   - Should show REAL provider networks from graph analysis
   - NOT mock fraud rings
3. Go to **Providers** tab
   - Search for real facility name (not just numbers)
   - Should return actual match from 318K providers
4. Go to **Pattern Analysis** tab
   - Should show REAL POL violations
   - NOT placeholder graphs

---

## STEP 10: Production Verification Checklist

```bash
# Run verification script
python backend/scripts/verify_production.py

# Results should show:
# ✅ Claims: 77,300,000+
# ✅ Providers: 318,794+
# ✅ High-value claims: 1,000,000+
```

---

## Critical Production Settings

| Setting | Development | Production |
|---------|-------------|------------|
| ENVIRONMENT | development | production |
| DEBUG | true | false |
| Database Mock Fallbacks | Enabled | **DISABLED** |
| Error Logging | Console | File + Sentry |
| Cache | In-Memory | Redis |
| Database Pool | 10 | 50+ |
| Workers | 1 | 4+ |

---

## Troubleshooting Production Issues

### Issue: API Returns Empty Results
```bash
# Check database has data
docker exec medicaid_postgres psql -U postgres -d medicaid_db \
  -c "SELECT COUNT(*) FROM claims;"

# If 0: data not loaded
# If >77M: query might be filtered too aggressively
```

### Issue: "Connection refused"
```bash
# Verify PostgreSQL running
docker ps | grep postgres

# Check DATABASE_URL
echo $DATABASE_URL

# Test connection directly
psql $DATABASE_URL -c "SELECT 1;"
```

### Issue: Dashboard Shows Synthetic Data
```bash
# Check if mock interceptor still active
grep -r "generate_mock\|DEMO_MODE" frontend/src/

# Check API response is from database
curl http://localhost:8000/api/providers | jq '.providers[0]'

# Should have real NPI, name, address (not placeholders)
```

---

## Production Monitoring

Add logging to track real data usage:

```python
@app.get("/api/analytics/sadc/attendance-heatmap")
def get_sadc_heatmap(db: Session = Depends(get_db)):
    """Log every request to verify production use."""
    logger.info(f"SADC heatmap request - querying 77M claims")
    
    # ... real query ...
    
    logger.info(f"Returned {len(results)} real anomalies from database")
    return results
```

---

## Going Live: Deployment Sequence

1. ✅ Backup existing PostgreSQL database
2. ✅ Run `verify_production.py` - confirm 77M+ claims
3. ✅ Remove all mock data generators
4. ✅ Update API endpoints to throw errors (not return mock)
5. ✅ Set `ENVIRONMENT=production` in .env
6. ✅ Restart backend and frontend
7. ✅ Open dashboard - verify REAL data shows
8. ✅ Test each tab for real results
9. ✅ Monitor logs for any fallback attempts
10. ✅ Go live with confidence

---

## Your Production System Now:

✅ Uses **77.3M real Medicaid claims**
✅ Detects fraud from **real provider data**
✅ Returns **real, not synthetic, results**
✅ Shows **actual fraud networks and patterns**
✅ Ready for **law enforcement/DOJ use**

**You're no longer in demo mode. This is production.**
