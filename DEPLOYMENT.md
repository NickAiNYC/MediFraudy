# MediFraudy — Deployment Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (optional, for caching)

## Environment Setup

1. **Copy the environment template:**
   ```bash
   cp .env.production.example .env
   ```

2. **Generate secrets:**
   ```bash
   # SECRET_KEY
   openssl rand -hex 32

   # Or using Python:
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Configure DATABASE_URL** with your PostgreSQL connection string.

4. **Set ENVIRONMENT=production** to enable production validations.

## Local Development

```bash
# Start services (PostgreSQL + Redis)
docker-compose up -d postgres redis

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn main:app --reload --port 8000

# In a separate terminal, start the frontend
cd frontend
npm install
npm start
```

## Running Tests

```bash
cd backend
DATABASE_URL=sqlite:///./test.db ENVIRONMENT=development \
  python -m pytest tests/ --ignore=tests/test_analytics.py -v
```

## Docker Deployment

```bash
# Build and start all services
docker-compose up --build -d

# Check health
curl http://localhost:8000/health
```

## Railway Deployment

1. Connect your GitHub repository to Railway.
2. Railway will auto-detect `railway.toml` for build/deploy config.
3. Add environment variables in the Railway dashboard:
   - `DATABASE_URL` — provision a PostgreSQL plugin or use an external DB
   - `SECRET_KEY` — generate with `openssl rand -hex 32`
   - `ENVIRONMENT` — set to `production`
   - `CORS_ORIGINS` — your frontend URL
4. Deploy. Railway uses the health check at `/health` to verify the service.

## Database Migrations (Alembic)

```bash
cd backend

# Create a new migration after model changes
alembic revision --autogenerate -m "Describe your change"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View migration history
alembic history
```

## Health Check

The `/health` endpoint verifies:
- Application status
- Database connectivity
- Current version and environment

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"2.1.0","environment":"production","checks":{"database":"connected"}}
```

## Security Checklist

- [ ] `SECRET_KEY` generated (32+ random bytes) — **never** use the default
- [ ] `DATABASE_URL` changed from default
- [ ] `.env` is in `.gitignore` — never commit secrets
- [ ] CORS configured with specific origins (not `*`)
- [ ] Sentry DSN configured for error tracking
- [ ] JWT tokens expire appropriately (`ACCESS_TOKEN_EXPIRE_MINUTES`)
