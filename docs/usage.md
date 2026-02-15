# Usage Guide

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (or use Docker)
- 16 GB RAM recommended for full dataset

### Environment Setup

```bash
cp .env.example .env
# Edit .env: set DB_PASSWORD, SECRET_KEY, MEDICAID_DATASET_URL
```

### Starting Services

```bash
# Option A: Docker (recommended)
docker-compose up -d

# Option B: Manual
# Start PostgreSQL, then:
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
cd frontend && npm install && npm start
```

## Loading Data

### Sample Data (Development)

```python
from data_ingestion.loader import detect_and_load

# Load first 100k rows for testing
import pandas as pd
df = pd.read_csv("data/medicaid_claims.csv", nrows=100000)
```

### Full Dataset

```python
from data_ingestion.loader import load_csv_chunks, detect_and_load

# Auto-detect zip or plain CSV/Parquet
df = detect_and_load("data/medicaid_claims.zip")

# Or process in chunks for the full 10 GB file
for chunk in load_csv_chunks("data/medicaid_claims.csv"):
    # Process each 50,000-row chunk
    pass
```

## Dashboard Navigation

| Page | URL | Description |
|------|-----|-------------|
| Provider Search | `/` | Search by name, NPI, or location |
| Anomalies | `/anomalies` | View outlier providers with Z-score filtering |
| Trends | `/trends` | Year-over-year billing trend charts |
| Cases | `/cases` | Whistleblower case management |
| Elderly Care | `/elderly-care` | Specialized dashboard for nursing homes/rehab |
| Provider Detail | `/providers/:id` | Detailed view with peer comparison |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/providers` | Search/list providers |
| GET | `/api/providers/:id` | Get provider detail |
| GET | `/api/anomalies` | List anomalies (filter by Z-score) |
| GET | `/api/analytics/stats` | Billing statistics |
| GET | `/api/analytics/outliers` | Detect outlier providers |
| GET | `/api/analytics/trends` | Year-over-year trends |
| GET | `/api/analytics/compare/:id` | Compare provider to peers |
| GET | `/api/analytics/fraud-patterns` | Detect fraud patterns |
| GET | `/api/cases` | List cases |
| POST | `/api/cases` | Create a case |
| POST | `/api/cases/:id/timeline` | Add timeline event |
| GET | `/api/export/provider/:id` | Export provider report |
