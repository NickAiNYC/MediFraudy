# MediFraudy — Medicaid Fraud Intelligence Platform

**Masterclass Engineered. Palantir-Weaponized. Built for Law Offices.**

MediFraudy transforms 77.3M Medicaid claims into actionable litigation intelligence for NYC qui tam attorneys and whistleblower law firms. It combines statistical anomaly detection, network graph analysis, and AI-powered legal reasoning to generate evidence packages ready for False Claims Act complaints.

## What This Does

| Capability | Description |
|---|---|
| **Risk Scoring Engine** | 6-component composite score (0-100) combining billing z-scores, peer deviation, temporal spikes, behavioral signals, network risk, and NYC-specific patterns |
| **Network Intelligence** | Graph-based fraud ring detection, kickback cycle identification, beneficiary concentration analysis |
| **Evidence Builder** | One-click litigation-ready evidence packages with auto-generated narratives, statistical comparisons, timelines |
| **DeepSeek Legal Assistant** | AI agent specialized in NYC Medicaid fraud law — False Claims Act, qui tam procedures, billing analysis |
| **NYC-Specific Detection** | Home care inflation, NEMT ghost rides, DME abuse, phantom visits, billing after death, cross-borough referral rings |
| **Borough Heatmap** | Risk visualization across Manhattan, Brooklyn, Queens, Bronx, and Staten Island |

## Recent NYC Prosecutions (What We Detect)

| Case | Amount | Date | Pattern |
|------|--------|------|---------|
| Queens adult day care | $120M charges | Feb 9, 2026 | Capacity violations |
| Brooklyn kickback scheme | $68M guilty pleas | Jan 15 & 28, 2026 | Referral rings |
| Albany Medicaid settlement | $1.3M | Feb 11, 2026 | Billing anomalies |

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env
# Edit .env — set DB_PASSWORD and optionally DEEPSEEK_API_KEY

# 2. Start services
docker-compose up -d

# 3. Install and run backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload

# 4. Install and run frontend
cd ../frontend && npm install && npm start
```

## Production Deployment (Railway)

MediFraudy is production-ready with enterprise-grade security, HIPAA compliance, and forensic integrity features.

### Quick Deploy to Railway

```bash
# 1. Connect to Railway
railway login

# 2. Initialize project
railway init

# 3. Add PostgreSQL and Redis
railway add --database postgresql
railway add --database redis

# 4. Set environment variables
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set JWT_SECRET_KEY=$(openssl rand -hex 32)
railway variables set ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 5. Deploy
git push origin main
```

**See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment guide.**

### Key Production Features

- **Multi-Service Architecture**: API + Background Workers + Scheduled Tasks
- **HIPAA Compliance**: PHI encryption at rest, audit logging, chain of custody
- **Evidence Integrity**: Cryptographic signing (SHA-256) for court admissibility
- **Security**: Rate limiting, JWT authentication, security headers, input sanitization
- **Monitoring**: Structured JSON logging, Sentry error tracking, health checks
- **Performance**: Redis caching, connection pooling, async background jobs
- **Forensics**: Immutable audit trails, evidence package verification

### DeepSeek AI Legal Assistant
Set `DEEPSEEK_API_KEY` in your `.env` to enable the AI legal assistant:
```env
DEEPSEEK_API_KEY=sk-your-key-here
```

## Architecture

```
MediFraudy/
├── backend/
│   ├── core/                 # Security (JWT/RBAC), structured logging
│   ├── services/             # Fraud intelligence services
│   │   ├── risk_scoring.py       # Composite fraud risk engine (0-100)
│   │   ├── anomaly_engine.py     # Billing spikes, duplicate claims, impossible density
│   │   ├── fraud_detection.py    # NYC-specific: home care, DME, CPT overuse, borough heatmap
│   │   ├── evidence_builder.py   # Litigation-ready case packages + narrative generation
│   │   ├── network_analysis.py   # Fraud ring detection, referral analysis
│   │   └── deepseek_agent.py     # DeepSeek AI legal assistant
│   ├── api/v1/routes/        # Versioned API endpoints
│   │   ├── intelligence.py       # Risk scores, anomalies, NYC signals, evidence packages
│   │   ├── auth.py               # JWT authentication
│   │   └── agent.py              # DeepSeek chat API
│   ├── analytics/            # Statistical, graph, pattern-of-life analysis
│   ├── models.py             # SQLAlchemy models + AuditLog
│   └── tests/                # 48+ tests
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── MasterDashboard   # Intelligence Overview
│       │   ├── Providers         # Provider Risk Index
│       │   ├── FraudRings        # Network Graph
│       │   ├── Cases             # Case Builder
│       │   ├── Alerts            # Real-time fraud alerts
│       │   ├── EvidenceVault     # Litigation evidence packages
│       │   ├── FraudAgent        # DeepSeek AI Legal Assistant
│       │   └── ...               # Pattern of Life, Home Care Intel
│       └── components/Layout     # Intelligence platform navigation
├── docker-compose.yml
└── docs/
```

## API Reference

### Intelligence API (v1)
```
POST /api/v1/auth/login                              # JWT authentication
GET  /api/v1/intelligence/risk-score/{provider_id}    # Composite risk score
GET  /api/v1/intelligence/risk-scores/batch           # Batch risk scoring
GET  /api/v1/intelligence/evidence-package/{id}       # Litigation-ready evidence
GET  /api/v1/intelligence/anomalies/billing-spikes/{id}
GET  /api/v1/intelligence/anomalies/impossible-density/{id}
GET  /api/v1/intelligence/anomalies/duplicate-claims/{id}
GET  /api/v1/intelligence/anomalies/billing-after-death/{id}
GET  /api/v1/intelligence/nyc/borough-heatmap
GET  /api/v1/intelligence/nyc/homecare-inflation/{id}
GET  /api/v1/intelligence/nyc/dme-abuse/{id}
GET  /api/v1/intelligence/nyc/cpt-overuse/{id}
GET  /api/v1/intelligence/nyc/cross-borough-referrals
POST /api/v1/agent/chat                               # DeepSeek legal assistant
GET  /api/v1/agent/status                              # Agent configuration status
```

### Risk Scoring Model
```json
{
  "risk_score": 82,
  "risk_level": "HIGH",
  "drivers": [
    "Billing 6.2x peer average",
    "Connected to 4 high-risk entities",
    "Procedure spike within 30 days"
  ],
  "sub_scores": {
    "billing_zscore": 85,
    "peer_deviation": 78,
    "temporal_spike": 92,
    "behavioral": 65,
    "network_risk": 80,
    "nyc_specific": 70
  }
}
```

Scoring bands: **0–39** Low · **40–69** Review · **70–100** High Litigation Risk

### Evidence Package Output
Includes: Provider profile, risk assessment, statistical peer comparison, suspicious activity timeline, claim breakdown by CPT code, network graph summary, anomaly list, and auto-generated litigation narrative.

### Litigation Narrative (Auto-Generated)
> "Provider Sunrise Adult Day Care (NPI: 1234567890), located in Queens, NY, has been identified with a composite fraud risk score of 94 out of 100 (HIGH risk). Statistical analysis shows billing at 4.8x the Queens peer average, with total claims of $12,450,000 across 3,200 submissions. Network analysis shows connections to 7 entities, including 3 high-risk entities."

## Security

- **JWT Authentication** with 4 RBAC roles: Partner, Associate, Investigator, Auditor
- **Audit logging** — who accessed what provider and when
- **Structured JSON logging** for production log aggregation
- **Input validation** on all API endpoints
- **No secrets in code** — all keys via environment variables

## Running Tests

```bash
cd backend
DATABASE_URL=sqlite:///test.db python -m pytest tests/ -v
```

## Qui Tam Legal Resources

> Qui tam provisions (31 U.S.C. §§ 3729-3733) allow private parties to file lawsuits on behalf of the government and receive **15-30%** of recovery.

## License

MIT
