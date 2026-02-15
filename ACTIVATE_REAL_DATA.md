# 🚀 Activate Real DOJ 11GB Data - Complete Guide

## Overview

Your MediFraudy dashboard is built to handle **real, massive datasets**. The system uses a chunked data ingestion pipeline that can process 11GB+ files efficiently.

---

## Step 1: Obtain the DOJ 11GB Dataset

### Where to Get Real Data:

1. **CMS Medicare Data** (Official)
   - URL: https://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/Medicare-Provider-Charge-Data
   - Format: CSV, Parquet
   - Size: ~11GB per year
   - Contains: Provider billing data, charges, services

2. **Medicaid Fraud Data (State-Specific)**
   - Contact your state Medicaid office
   - Often available as: CSV, Excel, or database exports
   - New York (NYS) releases periodic fraud lists

3. **OIG Exclusion List**
   - URL: https://oig.hhs.gov/exclusions/
   - CSV Format: https://oig.hhs.gov/exclusions/public.html
   - Contains: Excluded providers (fraud convictions)

4. **NHCAL (National Healthcare Anti-Fraud Association)**
   - https://www.nhcaa.org/
   - Provides fraud case data and patterns

---

## Step 2: Prepare Your Data

### File Format Support:
- ✅ CSV
- ✅ Parquet
- ✅ Excel
- ✅ ZIP (compressed)

### Required Columns:

```
PROVIDER COLUMNS:
- npi / provider_npi / billing_provider_npi_num (billing provider NPI)
- provider_name / provider_last_name_org
- provider_city
- provider_state
- provider_zip
- provider_type (e.g., "Adult Day Care", "Home Health")
- provider_street1 / address

CLAIM COLUMNS:
- claim_id
- beneficiary_id
- claim_date / service_date / claim_from_month
- billing_code / hcpcs_code
- amount / total_amount / line_payment_amount / total_paid
- units / total_claims
- place_of_service
```

**Note**: The loader automatically maps common column names (e.g., `hcpcs_code` -> `billing_code`). If your CSV uses custom headers, update `PROVIDER_MAPPING` and `CLAIM_MAPPING` in `backend/scripts/load_data.py`.

---

## Step 3: Load Data Using the CLI

### Basic Command:

```bash
cd backend
python scripts/load_data.py \
  --file /path/to/your/data.csv \
  --state NY \
  --chunksize 50000
```

### Advanced Options:

```bash
# Load with specific state filter
cd backend
python scripts/load_data.py \
  --file medicaid_claims_2024.csv \
  --state NY \
  --chunksize 100000 \
  --limit 1000000

# Load from ZIP file
cd backend
python scripts/load_data.py \
  --file claims_data.zip \
  --state NY \
  --chunksize 50000

# Download from URL and load
cd backend
python scripts/load_data.py \
  --url https://example.com/claims.csv \
  --state NY \
  --chunksize 50000
```

### Parameters:
- `--file`: Path to dataset (CSV, Parquet, Excel, or ZIP)
- `--state`: Filter by state (default: NY)
- `--chunksize`: Rows per batch (default: 50000)
- `--limit`: Max rows to load (for testing)
- `--url`: Download URL (optional)

---

## Step 4: Execute the Load

### Via Docker:

```bash
# Copy data into container
docker cp /path/to/data.csv medicaid_backend:/app/data.csv

# Load data
docker exec medicaid_backend python scripts/load_data.py \
  --file /app/data.csv \
  --state NY
```

### Via Local Backend:

```bash
cd backend

# Set database URL if needed (default matches docker-compose)
export DATABASE_URL="postgresql://analyst:change_this_in_production@localhost:5432/medicaid_db"

# Run loader
python scripts/load_data.py \
  --file /path/to/data.csv \
  --state NY \
  --chunksize 50000
```

---

## Step 5: Verify Data Load

### Check Database:

```bash
# Connect to PostgreSQL
psql postgresql://analyst:change_this_in_production@localhost:5432/medicaid_db

# Check provider count
SELECT COUNT(*) FROM providers;

# Check claim count
SELECT COUNT(*) FROM claims;

# Check state distribution
SELECT state, COUNT(*) FROM providers GROUP BY state;

# Check for fraud indicators
SELECT * FROM claims WHERE amount > 100000 LIMIT 10;
```

### Via Dashboard API:

```bash
# Get summary stats
curl http://localhost:8000/api/analytics/dashboard/summary

# Get provider count
curl http://localhost:8000/api/providers?limit=1

# Check data freshness
curl http://localhost:8000/api/analytics/stats
```

---

## Step 6: Enable Real-Time Scanning

### Set Up Live Data Sync:

**Option 1: Scheduled Data Updates**

Create `backend/scripts/sync_data.sh`:

```bash
#!/bin/bash

# Run daily at 2 AM
# Add to crontab: 0 2 * * * /path/to/sync_data.sh

DATE=$(date +%Y%m%d)
DATA_FILE="/data/medicaid_claims_$DATE.csv"

# Download latest data
wget -O $DATA_FILE https://cms.gov/data/latest.csv

# Load into database
python scripts/load_data.py \
  --file $DATA_FILE \
  --state NY \
  --chunksize 100000

# Run fraud detection
python scripts/run_analysis.py
```

**Option 2: Database Direct Connection**

Create `backend/config/data_sources.py`:

```python
# Direct database connection configuration
DATA_SOURCES = {
    'medicaid': {
        'type': 'postgresql',
        'host': 'cms-database.gov',
        'port': 5432,
        'database': 'medicaid_claims',
        'user': 'your_username',
        'password': 'your_password',
    },
    'cms': {
        'type': 'api',
        'base_url': 'https://api.cms.gov/data',
        'auth_token': 'your_api_key',
    }
}
```

---

## Step 7: Run Real-Time Fraud Detection

### Trigger Full Analysis:

```bash
cd backend
# Run a sweep of NYC elderly care facilities
python scripts/run_analysis.py --sweep --min-risk 70

# Or analyze a specific provider
python scripts/run_analysis.py --provider 12345 --days 365
```

### What Gets Analyzed:

✅ **Automated Transporter Classification**: During ingestion, NEMT providers are automatically classified by vehicle type (Ambulance, Ambulette, Taxi).
✅ **Pattern-of-Life violations**
✅ Capacity violations  
✅ SADC attendance anomalies
✅ CDPAP network fraud
✅ Pharmacy dumping
✅ NEMT ghost rides
✅ Recipient card sharing
✅ Billing anomalies

---

## Step 8: Monitor Dashboard for Real Data

### The dashboard will now show:

1. **Real Provider Statistics**
   - Actual provider locations
   - Real facility types
   - Genuine risk profiles

2. **Live Fraud Alerts**
   - Detected anomalies
   - Pattern matches
   - Network relationships

3. **Actual High-Risk Facilities**
   - Real facilities flagged
   - Justification details
   - Evidence trails

---

## Performance Optimization for 11GB Data

### Database Tuning:

```sql
-- Optimize for large scans
ALTER TABLE claims SET (fillfactor = 70);
CREATE INDEX idx_claims_amount ON claims(amount);
CREATE INDEX idx_claims_provider ON claims(provider_id);
CREATE INDEX idx_claims_date ON claims(claim_date);

-- Vacuum analyze
VACUUM ANALYZE claims;
```

### Connection Pooling:

```python
# In backend/database.py
pool_pre_ping = True
pool_size = 20
max_overflow = 40
```

### Chunk Sizing:
- **Small dataset (< 1GB)**: `--chunksize 100000`
- **Medium dataset (1-5GB)**: `--chunksize 50000`
- **Large dataset (5-11GB)**: `--chunksize 25000`

---

## Example: Load NYS Medicaid Data

### Complete Workflow:

```bash
# 1. Download NYS Medicaid fraud dataset
wget https://health.ny.gov/system/files/documents/2024/01/medicaid_providers.csv

# 2. Load into database
docker exec medicaid_backend python scripts/load_data.py \
  --file /app/medicaid_providers.csv \
  --state NY \
  --chunksize 50000

# 3. Run fraud analysis
docker exec medicaid_backend python scripts/run_analysis.py \
  --sweep \
  --min-risk 50

# 4. Check results in dashboard
# Open http://localhost:3000
# Navigate to "Fraud Rings" or "Pattern Analysis" tabs
# Real data will populate automatically
```

---

## Troubleshooting

### Issue: "Connection Timeout"
```bash
# Check database connection
psql postgresql://analyst:change_this_in_production@localhost:5432/medicaid_db
```

### Issue: "Missing Columns"
If you see errors about missing columns, check the mapping in `backend/scripts/load_data.py`. You can add your specific CSV headers to `PROVIDER_MAPPING` or `CLAIM_MAPPING`.

### Issue: "Out of Memory"
```bash
# Reduce chunk size
--chunksize 10000

# Or increase Docker memory
docker update --memory 8g medicaid_backend
```

### Issue: "Duplicate Key Errors"
```bash
# The loader uses upsert, but if you have duplicate claim_ids:
# Clear existing data first
docker exec medicaid_backend python -c "
from database import SessionLocal
from models import Claim, Provider
db = SessionLocal()
db.query(Claim).delete()
db.query(Provider).delete()
db.commit()
"
```

---

## Verify Real Data is Active

### Check Dashboard:

1. Go to **Overview** tab
2. Check "Risk Score Card" - should show real provider names
3. Go to **Providers** tab - search for real facilities
4. Check **Fraud Rings** - should show actual network connections

### CLI Verification:

```bash
# Check provider names (not synthetic)
curl http://localhost:8000/api/providers?limit=5 | jq '.providers[].name'

# Should show real names instead of "Provider 12345"
```

---

## Next Steps

1. ✅ **Obtain DOJ/CMS data** - Download from sources listed above
2. ✅ **Prepare CSV/Parquet** - Ensure required columns exist
3. ✅ **Run loader** - Execute load_data.py
4. ✅ **Verify load** - Check database and API
5. ✅ **Run analysis** - Execute run_analysis.py
6. ✅ **View results** - Open dashboard
7. ✅ **Set up automation** - Schedule daily/weekly updates

---

## Support & Resources

- **CMS Data**: https://www.cms.gov/Research-Statistics-Data-and-Systems
- **OIG Database**: https://oig.hhs.gov/exclusions/
- **Medicaid Fraud**: https://www.healthcoverage.org
- **NHCAA**: https://www.nhcaa.org/

---

**Your dashboard is production-ready for real data!** 🚀
