# 🚀 Activate Real DOJ 11GB Data - Quick Reference

## What You Have

Your MediFraudy system includes:

✅ **Production-Grade Data Pipeline**
- Handles 11GB+ files with chunked processing
- Auto-maps column names intelligently
- Supports CSV, Parquet, Excel, ZIP

✅ **Real-Time Fraud Detection**
- Pattern-of-Life analysis
- Network fraud rings
- Anomaly detection
- Statistical outliers

✅ **Live Dashboard**
- Updates as data loads
- Real-time analytics
- Interactive visualizations

---

## 3-Step Quick Start

### Step 1: Get Real Data
```bash
# Download from CMS (free, public)
wget https://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/Medicare-Provider-Charge-Data

# Or download NYS Medicaid fraud list
# Or use OIG Exclusion database
```

### Step 2: Load Data
```bash
# Make script executable
chmod +x load_real_data.sh

# Run the loader
./load_real_data.sh /path/to/your/data.csv NY
```

### Step 3: View Results
```
Open: http://localhost:3000
Navigate to: Fraud Rings OR Providers OR Pattern Analysis tabs
Real data will populate automatically!
```

---

## Manual Load (Advanced)

```bash
# Option 1: Via Docker
docker exec medicaid_backend python scripts/load_data.py \
  --file /app/data.csv \
  --state NY \
  --chunksize 50000

# Option 2: Direct Python
cd backend
python scripts/load_data.py \
  --file /path/to/data.csv \
  --state NY
```

---

## Verify Data Loaded

### Quick Check:
```bash
# Check provider count
curl http://localhost:8000/api/providers?limit=1 | jq '.count'

# Check dashboard summary
curl http://localhost:8000/api/analytics/dashboard/summary | jq '.top_risks'

# Database check
docker exec medicaid_postgres psql -U medicaid -d medicaid \
  -c "SELECT COUNT(*) as providers FROM providers;"
```

---

## Data Sources (Where to Get Real Data)

### 1. **CMS Medicare Data** (Best for testing)
- **URL**: https://www.cms.gov/Research-Statistics-Data-and-Systems
- **Size**: 11GB per year
- **Format**: CSV
- **Content**: Provider billing, services, charges
- **Free**: Yes

### 2. **OIG Exclusion List** (Fraud convictions)
- **URL**: https://oig.hhs.gov/exclusions/
- **Format**: CSV
- **Content**: Excluded providers (fraud cases)
- **Free**: Yes

### 3. **State Medicaid Data** (Most accurate)
- Contact your state Medicaid office
- Request: Provider billing data, claim data
- Format: Usually CSV or database

### 4. **NHCAA Database** (Fraud patterns)
- **URL**: https://www.nhcaa.org/
- Member access required
- Real fraud case data

---

## What Happens When You Load Real Data

### Dashboard Updates:
1. **Provider names** - Real facilities instead of "Provider 12345"
2. **Risk scores** - Actual calculated values from real data
3. **Fraud rings** - Real network connections detected
4. **Billing patterns** - Real anomalies flagged
5. **Geographic distribution** - Real facility locations

### New Analytics:
- SADC attendance patterns (real facilities)
- CDPAP caregiver networks (real relationships)
- Pharmacy dumping (real dumping patterns)
- NEMT ghost rides (real routes flagged)
- Recipient fraud (real patterns)

---

## Performance Settings

### For Different Dataset Sizes:

```bash
# Small dataset (< 1GB)
--chunksize 100000

# Medium dataset (1-5GB)
--chunksize 50000  # Default

# Large dataset (5-11GB)
--chunksize 25000

# Very large dataset (11GB+)
--chunksize 10000
--limit 5000000  # Load in stages
```

---

## Troubleshooting

### "Connection refused"
```bash
# Ensure containers are running
docker compose up -d

# Check database
docker exec medicaid_postgres psql -U medicaid -d medicaid -c "SELECT 1"
```

### "Out of memory"
```bash
# Increase Docker memory
docker update --memory 8g medicaid_backend
docker compose restart

# Or reduce chunk size
--chunksize 10000
```

### "File not found"
```bash
# Copy file to container first
docker cp /your/file.csv medicaid_backend:/app/data_import/

# Then load from container path
--file /app/data_import/file.csv
```

### "Duplicate key errors"
```bash
# Clear data first
./load_real_data.sh file.csv NY
# Answer 'y' to "Clear existing data?"
```

---

## Set Up Automated Daily Updates

### Create a cron job:

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 2 AM:
0 2 * * * /path/to/load_real_data.sh /path/to/medicaid_$(date +\%Y\%m\%d).csv NY >> /var/log/medfraudy.log 2>&1
```

### Or use Docker scheduler:

```bash
# Create backend/scripts/daily_sync.sh
#!/bin/bash
# Download latest data
wget https://cms.gov/latest_data.csv -O /app/latest.csv

# Load it
python scripts/load_data.py --file /app/latest.csv --state NY

# Run analysis
python scripts/run_analysis.py --state NY

# Email results
# (add your email integration here)
```

---

## Dashboard After Real Data Load

### You'll See:

**Overview Tab:**
- Real provider names and locations
- Actual risk scores calculated from real claims
- Real fraud patterns detected

**Providers Tab:**
- Search real facilities by name/NPI
- See actual billing history
- Real risk assessments

**Fraud Rings Tab:**
- Real provider networks
- Detected relationships
- Actual connections between facilities

**Pattern Analysis Tab:**
- Real behavioral patterns
- Actual capacity violations
- Real P-O-L violations

---

## Sample Real Data Format

If preparing your own CSV:

```
NPI,Provider_Name,City,State,Claim_ID,Claim_Date,Amount,Beneficiary_ID,Billing_Code,Units
1234567890,ABC Adult Day Care,New York,NY,CLM001,2024-01-01,5000,BEN001,90832,1
1234567891,XYZ Home Health,Buffalo,NY,CLM002,2024-01-02,3500,BEN002,99214,2
```

Required columns (auto-mapped):
- NPI, Provider_Name, City, State
- Claim_ID, Claim_Date, Amount, Beneficiary_ID, Billing_Code, Units

---

## Next Steps

1. **Download data** from CMS or state Medicaid
2. **Run loader**: `./load_real_data.sh [file] [state]`
3. **Wait for completion** (5-30 mins depending on size)
4. **Open dashboard**: http://localhost:3000
5. **See real results** - Fraud rings, patterns, anomalies

---

## Files Provided

- ✅ `ACTIVATE_REAL_DATA.md` - Complete detailed guide
- ✅ `load_real_data.sh` - Automated loader script
- ✅ `backend/scripts/load_data.py` - Core data loader
- ✅ `backend/scripts/run_analysis.py` - Fraud detection

---

## Support Resources

- **CMS Data Portal**: https://www.cms.gov/Research-Statistics-Data-and-Systems
- **OIG Database**: https://oig.hhs.gov/exclusions/public.html
- **Data Formats**: CSV, Parquet, Excel, ZIP all supported
- **Max File Size**: 11GB+ supported

---

**You're ready to activate real data! 🚀**

Questions? Check `ACTIVATE_REAL_DATA.md` for the complete guide.
