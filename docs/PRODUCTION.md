# 🚀 Production Deployment Guide

## Pre-Deployment Checklist

### 1. Database Configuration

**Replace Mock Session in `/backend/routes/homecare.py`:**

```python
# REMOVE THIS (lines 12-18):
# DEMO MODE - Mock database session
class Session:
    pass

def get_db():
    return Session()

# ADD THIS INSTEAD:
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/medicaid_fraud')

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Production database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2. Required Database Tables

**Create these tables in your database:**

```sql
-- Claims table
CREATE TABLE claims (
    claim_id BIGINT PRIMARY KEY,
    provider_id INT NOT NULL,
    beneficiary_id INT NOT NULL,
    aide_id INT,
    claim_date DATE NOT NULL,
    visit_start_time TIMESTAMP,
    visit_end_time TIMESTAMP,
    billed_minutes INT,
    amount DECIMAL(10,2),
    billing_code VARCHAR(10),
    modifiers VARCHAR(50),
    referring_provider INT,
    INDEX idx_provider (provider_id),
    INDEX idx_beneficiary (beneficiary_id),
    INDEX idx_claim_date (claim_date)
);

-- EVV Records table
CREATE TABLE evv_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    claim_id BIGINT NOT NULL,
    original_start_time TIMESTAMP,
    original_end_time TIMESTAMP,
    adjusted_start_time TIMESTAMP,
    adjusted_end_time TIMESTAMP,
    was_manually_adjusted BOOLEAN DEFAULT FALSE,
    adjustment_reason TEXT,
    adjusted_by VARCHAR(100),
    adjustment_timestamp TIMESTAMP,
    gps_latitude DECIMAL(10,8),
    gps_longitude DECIMAL(11,8),
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
    INDEX idx_claim (claim_id)
);

-- Hospital Admissions table
CREATE TABLE hospital_admissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    beneficiary_id INT NOT NULL,
    admission_date DATE NOT NULL,
    discharge_date DATE,
    facility_name VARCHAR(200),
    diagnosis_codes TEXT,
    INDEX idx_beneficiary (beneficiary_id),
    INDEX idx_dates (admission_date, discharge_date)
);

-- Beneficiaries table
CREATE TABLE beneficiaries (
    id INT PRIMARY KEY,
    name VARCHAR(200),
    age INT,
    diagnosis_codes TEXT,
    medicare_status VARCHAR(50),
    INDEX idx_age (age)
);

-- Physician Visits table
CREATE TABLE physician_visits (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    beneficiary_id INT NOT NULL,
    physician_id INT NOT NULL,
    visit_date DATE NOT NULL,
    visit_type VARCHAR(50),
    diagnosis_codes TEXT,
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(id),
    INDEX idx_beneficiary (beneficiary_id),
    INDEX idx_visit_date (visit_date)
);

-- Homebound Certifications table
CREATE TABLE homebound_certifications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    beneficiary_id INT NOT NULL,
    physician_id INT NOT NULL,
    physician_name VARCHAR(200),
    certification_date DATE NOT NULL,
    expiration_date DATE,
    certification_reason TEXT,
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(id),
    INDEX idx_beneficiary (beneficiary_id),
    INDEX idx_physician (physician_id)
);

-- Aides table
CREATE TABLE aides (
    id INT PRIMARY KEY,
    name VARCHAR(200),
    license_number VARCHAR(50),
    hire_date DATE,
    provider_id INT NOT NULL,
    INDEX idx_provider (provider_id)
);

-- Aide Time Off table
CREATE TABLE aide_time_off (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    aide_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    vacation_type VARCHAR(50),
    approved_by VARCHAR(100),
    FOREIGN KEY (aide_id) REFERENCES aides(id),
    INDEX idx_aide (aide_id),
    INDEX idx_dates (start_date, end_date)
);

-- Recruiters table
CREATE TABLE recruiters (
    id INT PRIMARY KEY,
    name VARCHAR(200),
    license_number VARCHAR(50),
    provider_id INT NOT NULL
);

-- Recruiter Assignments table
CREATE TABLE recruiter_assignments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    recruiter_id INT NOT NULL,
    beneficiary_id INT NOT NULL,
    recruitment_date DATE NOT NULL,
    referral_source VARCHAR(100),
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(id),
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(id),
    INDEX idx_recruiter (recruiter_id),
    INDEX idx_beneficiary (beneficiary_id)
);
```

### 3. Environment Variables

**Create `.env` file:**

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/medicaid_fraud

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/fraud-detection/api.log

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
```

### 4. Update Main Application

**In `/backend/main.py`, add home care routes:**

```python
from routes.graph import router as graph_router
from routes.homecare import router as homecare_router  # ADD THIS

app = FastAPI(...)

app.include_router(graph_router)
app.include_router(homecare_router)  # ADD THIS
```

### 5. Install Production Dependencies

**Add to `/backend/requirements.txt`:**

```txt
# Existing dependencies...

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
alembic==1.13.0

# Production server
gunicorn==21.2.0

# Monitoring
sentry-sdk==1.39.1
prometheus-client==0.19.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### 6. Security Hardening

**Add authentication to routes:**

```python
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token."""
    # Implement JWT verification
    pass

# Add to endpoints:
@router.get("/comprehensive-analysis/{provider_id}")
async def comprehensive_homecare_analysis(
    provider_id: int,
    credentials: HTTPAuthorizationCredentials = Security(security),  # ADD THIS
    db: Session = Depends(get_db)
):
    await verify_token(credentials)  # ADD THIS
    # ... rest of code
```

### 7. Data Loading Scripts

**Create `/backend/scripts/load_data.py`:**

```python
"""
Script to load public Medicaid data into database.
Run: python scripts/load_data.py --source /path/to/data
"""

import pandas as pd
import argparse
from sqlalchemy import create_engine
from datetime import datetime

def load_claims_data(file_path: str, engine):
    """Load claims from CSV/Parquet."""
    print(f"Loading claims from {file_path}...")
    
    # Adjust based on your data format
    df = pd.read_csv(file_path)
    
    # Map columns to database schema
    claims_df = df.rename(columns={
        'ClaimID': 'claim_id',
        'ProviderID': 'provider_id',
        'BeneficiaryID': 'beneficiary_id',
        # ... map other columns
    })
    
    # Load to database
    claims_df.to_sql('claims', engine, if_exists='append', index=False)
    print(f"Loaded {len(claims_df)} claims")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='Path to data directory')
    parser.add_argument('--db-url', required=True, help='Database URL')
    args = parser.parse_args()
    
    engine = create_engine(args.db_url)
    
    # Load each data type
    load_claims_data(f"{args.source}/claims.csv", engine)
    # load_evv_data(...)
    # load_beneficiaries(...)
    
    print("Data loading complete!")

if __name__ == "__main__":
    main()
```

### 8. Docker Deployment

**Create `Dockerfile`:**

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

**Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: medicaid_fraud
      POSTGRES_USER: fraud_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://fraud_user:${DB_PASSWORD}@postgres:5432/medicaid_fraud
    depends_on:
      - postgres
    restart: always

volumes:
  postgres_data:
```

### 9. Testing

**Create `/backend/tests/test_homecare.py`:**

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_evv_fraud_endpoint():
    response = client.get("/api/homecare/evv-fraud/1")
    assert response.status_code == 200
    data = response.json()
    assert 'provider_id' in data
    assert 'total_suspicious' in data

def test_comprehensive_analysis():
    response = client.get("/api/homecare/comprehensive-analysis/1")
    assert response.status_code == 200
    data = response.json()
    assert 'risk_score' in data
    assert 0 <= data['risk_score'] <= 100

def test_batch_analysis():
    response = client.get("/api/homecare/batch-analysis?provider_ids=1,2,3")
    assert response.status_code == 200
    data = response.json()
    assert 'total_providers_analyzed' in data

# Run: pytest tests/
```

### 10. Monitoring & Logging

**Add to `main.py`:**

```python
import sentry_sdk
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

# Sentry error tracking
sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'))

# Prometheus metrics
api_requests = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method'])
api_latency = Histogram('api_latency_seconds', 'API latency', ['endpoint'])

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🚀 Deployment Steps

### Development
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Staging
```bash
docker-compose up -d
# Load test data
python scripts/load_data.py --source /data --db-url $DATABASE_URL
# Run tests
pytest tests/
```

### Production
```bash
# AWS/GCP/Azure deployment
# 1. Set environment variables
# 2. Deploy with Docker/Kubernetes
# 3. Configure load balancer
# 4. Enable SSL/TLS
# 5. Set up monitoring
```

## ✅ Production Readiness Checklist

- [ ] Database tables created
- [ ] Environment variables configured
- [ ] Mock session replaced with real DB
- [ ] Authentication implemented
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Error tracking (Sentry) set up
- [ ] Tests passing
- [ ] SSL/TLS configured
- [ ] Backup strategy in place
- [ ] Monitoring dashboard created
- [ ] Documentation updated

---

**After deployment, the API will be production-ready for law firm licensing!** 🚀
