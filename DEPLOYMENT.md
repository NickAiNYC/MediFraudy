# MediFraudy Production Deployment Guide

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository access
- Domain name (optional)
- PostgreSQL database URL (Railway provides this)
- Redis URL (Railway provides this)

## Quick Start

### Step 1: Create Railway Project

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select `NickAiNYC/MediFraudy`
4. Railway will auto-detect configuration from `railway.toml`

### Step 2: Add PostgreSQL Database

1. In Railway project dashboard, click "New"
2. Select "Database" → "PostgreSQL"
3. Database will provision automatically
4. Connection string available as `${{Postgres.DATABASE_URL}}`

### Step 3: Add Redis

1. Click "New" → "Database" → "Redis"
2. Connection string available as `${{Redis.REDIS_URL}}`

### Step 4: Configure Environment Variables

In Railway project settings → "Variables", add:

```bash
# Required
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENCRYPTION_KEY=<generate-with-python-cryptography-fernet>

# Optional
DEEPSEEK_API_KEY=sk-your-key
SENTRY_DSN=https://your-sentry-dsn
CORS_ORIGINS=https://yourdomain.com

# Feature Flags
RATE_LIMIT_ENABLED=true
ENABLE_BACKGROUND_JOBS=true
ENABLE_EVIDENCE_SIGNING=true
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

**Generate encryption keys:**
```bash
# SECRET_KEY and JWT_SECRET_KEY
openssl rand -hex 32

# ENCRYPTION_KEY (Fernet key)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 5: Deploy

1. Railway auto-deploys on git push to main branch
2. Monitor deployment logs in Railway dashboard
3. First deployment takes ~5-10 minutes

### Step 6: Run Database Migrations

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Run migrations (if using Alembic)
railway run alembic upgrade head

# Or initialize database tables
railway run python -c "from backend.database import init_db; init_db()"
```

### Step 7: Verify Deployment

```bash
# Check health endpoint
curl https://your-app.up.railway.app/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2026-02-15T...",
  "checks": {
    "database": "connected",
    "redis": "connected"
  }
}

# Run validation script
./scripts/validate_deployment.sh https://your-app.up.railway.app
```

### Step 8: Create First User

```bash
# SSH into Railway container
railway run bash

# Create admin user
python -c "
from backend.database import SessionLocal
from backend.models import User
from backend.core.security import get_password_hash

db = SessionLocal()
admin = User(
    email='your-email@lawfirm.com',
    hashed_password=get_password_hash('YourSecurePassword123!'),
    role='Partner',
    is_active=True
)
db.add(admin)
db.commit()
print('Admin user created')
"
```

## Advanced Configuration

### Multi-Service Deployment

Railway.toml configures three services:
- **API**: Main FastAPI application
- **Worker**: Celery background job processor
- **Beat**: Celery scheduler for periodic tasks

All services are deployed automatically.

### Custom Domain

1. Railway dashboard → Settings → Domains
2. Click "Add Domain"
3. Add your domain (e.g., app.medifraudy.com)
4. Update DNS:
   - Type: CNAME
   - Name: app
   - Value: your-app.up.railway.app
5. SSL certificate auto-provisioned

### Environment-Specific Variables

Railway automatically injects:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `PORT` - Application port (Railway manages this)
- `RAILWAY_ENVIRONMENT` - Environment name

## Monitoring

### Health Checks

Railway automatically monitors `/health` endpoint every 30 seconds.

### Application Logs

```bash
# Follow logs in real-time
railway logs --follow

# Filter by service
railway logs api
railway logs worker
railway logs beat
```

### Sentry Integration

Add Sentry DSN to environment variables for error tracking:

```bash
SENTRY_DSN=https://your-sentry-key@sentry.io/project-id
```

## Backup Strategy

### Database Backups

Railway PostgreSQL includes automatic daily backups.

**Manual backup:**
```bash
railway run pg_dump $DATABASE_URL > backup.sql
```

**Restore:**
```bash
railway run psql $DATABASE_URL < backup.sql
```

### Evidence Package Backups

Recommended: Store evidence packages in S3/GCS for long-term retention.

## Scaling

### Vertical Scaling

Railway dashboard → Settings → Resources
- Adjust CPU and memory allocation

### Horizontal Scaling

In `railway.toml`, increase replicas:
```toml
[deploy]
numReplicas = 3
```

## Troubleshooting

### Deployment Fails

Check logs:
```bash
railway logs
```

Common issues:
- Missing environment variables → Add in Railway settings
- Database connection errors → Verify DATABASE_URL is set
- Port binding issues → Railway uses $PORT env var automatically

### Database Connection Issues

Test connection:
```bash
railway run bash
python -c "from backend.database import engine; engine.connect()"
```

### Rate Limit Issues

If Redis is unavailable, rate limiting falls back to in-memory mode.
For production, ensure Redis is properly configured.

### Health Check Failures

1. Check application logs: `railway logs api`
2. Verify database is accessible
3. Ensure all required environment variables are set
4. Check resource limits (CPU/memory)

## Security Checklist

- [ ] All secrets in environment variables (not in code)
- [ ] CORS restricted to production domain
- [ ] Rate limiting enabled
- [ ] Database backups configured
- [ ] SSL certificate active
- [ ] Audit logging enabled
- [ ] PHI encryption verified (ENCRYPTION_KEY set)
- [ ] Sentry error tracking configured

## Performance Optimization

### Database Connection Pooling

Configured in `backend/database.py`:
- Pool size: 20 connections
- Max overflow: 10 connections
- Connection recycling: 3600 seconds

### Redis Caching

- Risk scores cached for 1 hour
- Peer baselines cached for 24 hours
- Network insights cached for 30 minutes

### Background Jobs

Celery handles:
- Evidence package generation (async)
- Batch risk score updates (nightly at 2 AM)
- Audit log cleanup (weekly)

## HIPAA Compliance

### PHI Encryption

All PHI fields encrypted at rest using Fernet (AES-128):
- Patient SSN
- Patient names
- Date of birth

Ensure `ENCRYPTION_KEY` environment variable is set.

### Audit Logging

All access to PHI is logged in `audit_logs` table:
- Who accessed data
- When accessed
- What was accessed
- IP address

### Data Retention

- Audit logs: 7 years (HIPAA requirement)
- Evidence packages: Permanent
- Claims data: As required by legal hold

## Support

Issues? Contact:
- GitHub: https://github.com/NickAiNYC/MediFraudy/issues
- Email: support@medifraudy.com

## Additional Resources

- Railway Docs: https://docs.railway.app
- FastAPI Docs: https://fastapi.tiangolo.com
- Celery Docs: https://docs.celeryproject.org
