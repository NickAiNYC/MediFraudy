# Medicaid Whistleblower Analytics

Analyze the HHS DOGE Medicaid dataset (10.32 GB, provider-level claims 2018–2024) with a focus on NYC elderly care and rehabilitation facilities.

## Critical Urgency Context

The dataset was released **February 13, 2026**. Recent prosecutions demonstrate the government is moving fast on elderly care fraud:

| Case | Amount | Date |
|------|--------|------|
| Queens adult day care | $120M charges | Feb 9, 2026 |
| Brooklyn kickback scheme | $68M guilty pleas | Jan 15 & 28, 2026 |
| Albany Medicaid settlement | $1.3M | Feb 11, 2026 |

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env
# Edit .env with your DB_PASSWORD

# 2. Start services
docker-compose up -d

# 3. Install backend dependencies
cd backend && pip install -r requirements.txt

# 4. Run backend
uvicorn main:app --reload

# 5. Install and run frontend
cd ../frontend && npm install && npm start
```

## Project Structure

```
medicaid-whistleblower-analytics/
├── backend/                  # FastAPI + Python analytics
│   ├── analytics/            # Statistical, comparison, fraud pattern detection
│   ├── data_ingestion/       # Loader (zip/csv/parquet), validator, transformer
│   ├── tests/                # pytest test suite
│   ├── main.py               # FastAPI application
│   ├── models.py             # SQLAlchemy ORM models
│   ├── config.py             # Environment variable management
│   └── database.py           # PostgreSQL connection
├── frontend/                 # React + TypeScript dashboard
│   └── src/
│       ├── components/       # ProviderSearch, AnomalyTable, TrendChart, etc.
│       ├── pages/            # ElderlyCareDashboard
│       └── services/         # API client
├── data/                     # Dataset files (git-ignored)
├── notebooks/                # Jupyter exploratory analysis
├── docs/                     # Usage guide, whistleblower guide
├── docker-compose.yml        # PostgreSQL + backend + frontend
└── .github/workflows/        # CI setup
```

## Processing 10.32 GB Dataset

The full dataset is ~10 GB uncompressed. Recommended approach:

- **Automatic Download**: Use `MedicaidDataLoader` for automatic download with progress bar and checksum verification
- **Development**: Use `--sample=100000` flag to load 100k rows for testing
- **Production**: Use chunking (already implemented in `loader.py`)
- **Resources**: Minimum 16 GB RAM recommended for full load
- **Alternative**: Use Polars or Dask if pandas memory issues occur
- **Zip support**: The loader auto-detects `.zip` archives and extracts the first CSV/Parquet inside

### Data Ingestion

```python
from data_ingestion.loader import MedicaidDataLoader, detect_and_load, load_csv_chunks

# Method 1: Auto-download with checksum verification (RECOMMENDED)
loader = MedicaidDataLoader(
    file_path="data/medicaid_claims.zip",
    url="https://data.medicaid.gov/dataset.zip",
    expected_checksum="your_sha256_checksum_here"
)
df = loader.ensure_data()  # Downloads if missing, verifies, loads

# Method 2: Manual - Auto-detect zip or plain file
df = detect_and_load("data/medicaid_claims.zip")

# Method 3: Process in memory-efficient chunks
for chunk in load_csv_chunks("data/medicaid_claims.csv", chunk_size=50000):
    process(chunk)
```

## Key Features

### Pattern-of-Life Forensic Intelligence Layer
NEW! Advanced forensic analysis based on recent prosecution patterns:
- **Behavioral Pattern Analysis**: Detect weekend/holiday billing anomalies and suspicious batch submissions
- **Capacity Violation Detection**: Identify billing exceeding licensed facility capacity (Queens $120M case pattern)
- **Kickback Scheme Indicators**: Find beneficiary concentration and enrollment spikes (Brooklyn $68M case pattern)
- **Comprehensive Risk Scoring**: Composite risk assessment combining all pattern modules
- **NYC Elderly Care Sweep**: Automated analysis of all NYC facilities

Access via API endpoints:
```python
# Get comprehensive pattern-of-life analysis for a provider
GET /api/analytics/pattern-of-life/{provider_id}

# Run NYC-wide elderly care facility sweep
GET /api/analytics/nyc-elderly-care-sweep?min_risk_score=50&limit=100
```

### Enhanced Data Loader
Automatic download with checksum verification:
```python
from data_ingestion.loader import MedicaidDataLoader

loader = MedicaidDataLoader(
    file_path="data/medicaid_claims.zip",
    url="https://example.com/dataset.zip",
    expected_checksum="abc123..."  # SHA-256
)
df = loader.ensure_data()  # Downloads if missing, verifies checksum, loads data
```

### Analytics Engine
- **Statistical analysis**: Mean, median, std deviation per billing code in NY
- **Outlier detection**: Z-score thresholds at 3, 4, and 5 sigma
- **Year-over-year trends**: Detect billing volume changes across 2018–2024
- **Fraud pattern detection**: Sustained high-volume billing, unusual code combinations, weekend/holiday anomalies, capacity violations, kickback indicators

### Target Billing Codes (from recent prosecutions)

| Category | Codes |
|----------|-------|
| Adult Day Care | T2024, T2025, S5100, S5101, S5102, S5105 |
| Home Health | G0151–G0159 |
| Capacity Related | T2024, T2025 |

### Whistleblower Case Management
- Secure note-taking for specific facilities
- Evidence timeline builder
- Export functionality for attorney packages
- Anonymized reporting option

## Qui Tam Legal Resources

| Firm | Contact | Specialty |
|------|---------|-----------|
| Phillips & Cohen | (212) 220-7110 | False Claims Act |
| Constantine Cannon | (212) 350-2700 | Whistleblower representation |
| Kirby McInerney | investigations@kmllp.com | Healthcare fraud |

> Qui tam provisions allow private parties to file lawsuits on behalf of the government and receive up to 30% of recovery.

## Running Tests

```bash
# Backend (10 tests for pattern-of-life module)
cd backend && python -m pytest tests/ -v

# Frontend
cd frontend && npm test

# TypeScript compilation check
cd frontend && npx tsc --noEmit
```

## API Endpoints

### Pattern-of-Life Analytics
```
GET /api/analytics/pattern-of-life/{provider_id}
    - Comprehensive forensic analysis (behavioral, capacity, kickback)
    - Query params: lookback_days (default: 365, range: 30-1825)

GET /api/analytics/capacity-violations/{provider_id}
    - Detect billing exceeding licensed capacity (Queens case pattern)

GET /api/analytics/kickback-patterns/{provider_id}
    - Detect beneficiary concentration and enrollment spikes

GET /api/analytics/behavioral-patterns/{provider_id}
    - Analyze weekend billing and batch submission patterns

GET /api/analytics/nyc-elderly-care-sweep
    - Analyze all NYC elderly care facilities
    - Query params: min_risk_score (default: 50), limit (default: 100)
```

### Core Analytics
```
GET /api/providers
    - Search providers with filters

GET /api/anomalies
    - List detected anomalies with z-score filtering

GET /api/analytics/stats
    - Billing statistics by state and code

GET /api/analytics/fraud-patterns
    - Detect known fraud patterns

GET /api/cases
    - Whistleblower case management

GET /api/export/provider/{provider_id}
    - Export provider report
```

## License

MIT
