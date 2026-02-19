# Railway Data Loading Guide — 77M Medicaid Claims (3.6GB ZIP)

## Problem

Your 3.6GB compressed ZIP file with 77 million Medicaid claims crashes Railway because:

1. **Memory Limits**: Railway free tier = 512MB RAM, Pro = 8GB. Your uncompressed CSV is ~12-15GB.
2. **Ephemeral Storage**: Railway containers have temporary filesystems that reset on deploy.
3. **Request Timeouts**: 10-minute limit for HTTP requests, but data loading takes 2-4 hours.

## Solution: Streaming + Background Loading

We've implemented a Railway-optimized data loader that:

- ✅ **Streams from ZIP** without extracting to disk
- ✅ **Processes in 10k row chunks** (max 50MB RAM per chunk)
- ✅ **Runs as Celery background task** (no timeout)
- ✅ **Saves checkpoints every 50k rows** (resume on crash)
- ✅ **Tracks progress in Redis** (monitor via API)

---

## Step 1: Set Up Railway Volumes

Railway volumes provide **persistent storage** that survives deploys.

### Create Volume via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Create a volume for data storage
railway volume create data-volume --mount-path /data

# Verify volume
railway volume list
```

### Or via Railway Dashboard

1. Go to your Railway project
2. Click on your service → **Settings**
3. Scroll to **Volumes** section
4. Click **+ New Volume**
5. Name: `data-volume`
6. Mount Path: `/data`
7. Size: **10GB** (minimum for 3.6GB ZIP + working space)

---

## Step 2: Upload Your ZIP File to Railway Volume

You have **three options** to get your 3.6GB file onto Railway:

### Option A: Upload via Railway CLI (Recommended)

```bash
# Upload file to Railway volume
railway run bash

# Inside Railway container:
cd /data
curl -o medicaid_claims.zip "YOUR_DOWNLOAD_URL"

# Or if you have the file locally, use scp/sftp
# (Railway doesn't support direct file upload yet)
```

### Option B: Download from External Storage

Upload your ZIP to cloud storage first, then download on Railway:

```bash
# 1. Upload to S3/GCS/Dropbox/Google Drive
# 2. Get public download URL
# 3. SSH into Railway and download:

railway run bash
cd /data
wget "https://your-storage-url/medicaid_claims.zip"

# Or use curl
curl -L -o medicaid_claims.zip "https://your-storage-url/medicaid_claims.zip"
```

### Option C: Use Railway's File Upload (Small Files Only)

For files < 500MB, you can use Railway's web interface:
1. Railway Dashboard → Service → Files
2. Upload to `/data/` directory

**Note**: This won't work for 3.6GB files due to browser limits.

---

## Step 3: Deploy Multi-Service Railway Configuration

Your app needs **3 separate Railway services**:

### Create `railway.json` (Multi-Service Config)

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Create Separate Services in Railway Dashboard

#### Service 1: API (FastAPI)

```toml
# railway-api.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "cd backend && gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120"
healthcheckPath = "/health"
healthcheckTimeout = 30
```

#### Service 2: Worker (Celery)

```toml
# railway-worker.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "cd backend && celery -A tasks.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=100"
```

#### Service 3: Beat (Celery Scheduler)

```toml
# railway-beat.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "cd backend && celery -A tasks.celery_app beat --loglevel=info"
```

### Set Environment Variables (All Services)

```bash
# Database (Railway auto-injects)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENCRYPTION_KEY=<generate-with-fernet>

# Data loading
MEDICAID_DATASET_PATH=/data/medicaid_claims.zip

# Performance tuning for Railway
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
CHUNK_SIZE=10000
```

---

## Step 4: Start Data Loading

### Via API (Recommended)

```bash
# 1. Get JWT token
curl -X POST https://your-app.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@law.com", "password": "your-password"}'

# 2. Start data loading
curl -X POST https://your-app.railway.app/api/v1/data-loading/start \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zip_path": "/data/medicaid_claims.zip",
    "state_filter": "NY",
    "resume": true,
    "max_rows": null
  }'

# Response:
{
  "task_id": "abc-123-def-456",
  "status": "started",
  "message": "Data loading started. Task ID: abc-123-def-456",
  "estimated_hours": 3.5
}
```

### Via Railway CLI

```bash
railway run python backend/scripts/load_railway_data.py
```

---

## Step 5: Monitor Progress

### Check Progress via API

```bash
# Get current progress
curl https://your-app.railway.app/api/v1/data-loading/progress \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
{
  "task_id": "abc-123-def-456",
  "status": "loading",
  "rows_loaded": 2500000,
  "last_checkpoint": 2500000,
  "updated_at": "2026-02-16T19:45:00Z",
  "file_size_gb": 3.6
}
```

### Monitor Celery Worker Logs

```bash
# Follow worker logs in real-time
railway logs --service worker --follow

# You'll see:
# INFO: Processing chunk 250/7700
# INFO: Checkpoint: 2,500,000 rows processed, 1,850,000 claims inserted
```

### Check Database Stats

```bash
curl https://your-app.railway.app/api/v1/data-loading/stats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
{
  "providers": {
    "total": 125000,
    "nyc": 8500,
    "by_state": [
      {"state": "NY", "count": 45000},
      {"state": "CA", "count": 32000}
    ]
  },
  "claims": {
    "total": 1850000,
    "earliest_date": "2020-01-01",
    "latest_date": "2025-12-31"
  }
}
```

---

## Step 6: Resume on Crash (If Needed)

If Railway crashes or restarts during loading:

```bash
# Resume from last checkpoint
curl -X POST https://your-app.railway.app/api/v1/data-loading/resume \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "abc-123-def-456"}'

# Response:
{
  "task_id": "xyz-789-new",
  "status": "resumed",
  "message": "Resuming from row 2,500,000",
  "previous_task_id": "abc-123-def-456"
}
```

The loader will:
1. Read last checkpoint from Redis
2. Skip already-processed rows
3. Continue from where it left off

---

## Performance Expectations

### Railway Free Tier (512MB RAM, Shared CPU)

- **Speed**: ~300-500 rows/second
- **Time**: 4-6 hours for 77M rows
- **Memory**: 50-100MB peak per chunk
- **Crashes**: Possible due to memory limits, use resume

### Railway Pro Tier (8GB RAM, Dedicated CPU)

- **Speed**: ~1,000-2,000 rows/second
- **Time**: 2-3 hours for 77M rows
- **Memory**: 200-500MB peak
- **Crashes**: Rare, stable loading

### Optimization Tips

1. **Filter by State**: Load only NY data first (reduces to ~15M rows)
   ```json
   {"state_filter": "NY"}
   ```

2. **Test with Sample**: Verify setup with 100k rows first
   ```json
   {"max_rows": 100000}
   ```

3. **Increase Chunk Size** (Pro tier only):
   ```bash
   CHUNK_SIZE=50000  # Default is 10000
   ```

4. **Monitor Memory**:
   ```bash
   railway logs --service worker | grep "Memory"
   ```

---

## Troubleshooting

### Issue: "ZIP file not found"

**Solution**: Verify volume mount and file path

```bash
railway run bash
ls -lh /data/
# Should show: medicaid_claims.zip
```

### Issue: "Worker keeps crashing"

**Cause**: Out of memory on free tier

**Solutions**:
1. Reduce chunk size: `CHUNK_SIZE=5000`
2. Upgrade to Pro tier (8GB RAM)
3. Filter to single state: `state_filter="NY"`

### Issue: "Database connection pool exhausted"

**Solution**: Reduce pool size for Railway

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=2
```

### Issue: "Loading is too slow"

**Solutions**:
1. Upgrade to Railway Pro (dedicated CPU)
2. Increase Celery concurrency: `--concurrency=4`
3. Disable fraud detection during load: `add_fraud_features=False`

### Issue: "Redis connection failed"

**Solution**: Ensure Redis service is running

```bash
railway services
# Should show: postgres, redis, api, worker, beat

# Restart Redis if needed
railway restart --service redis
```

---

## Alternative: Load Data Locally, Then Dump to Railway

If Railway loading is too slow, load locally and dump to Railway:

```bash
# 1. Load data on your local machine (faster)
cd backend
python scripts/load_data.py \
  --file ~/Downloads/medicaid_claims.zip \
  --state NY \
  --chunksize 50000

# 2. Dump PostgreSQL database
pg_dump medicaid_db > medicaid_dump.sql

# 3. Upload to Railway
railway run bash
psql $DATABASE_URL < medicaid_dump.sql
```

**Pros**: Much faster (local SSD vs Railway network)
**Cons**: Requires local PostgreSQL and 15GB+ disk space

---

## Verification

After loading completes, verify data:

```bash
# Check counts
curl https://your-app.railway.app/api/v1/data-loading/stats

# Test fraud detection
curl https://your-app.railway.app/api/v1/intelligence/risk-scores/batch?limit=10

# View dashboard
open https://your-app.railway.app
```

---

## Cost Estimate

### Railway Free Tier
- **Storage**: 1GB included (need Pro for 10GB volume)
- **Compute**: $5/month after free hours
- **Database**: 512MB included
- **Total**: ~$5-10/month

### Railway Pro Tier (Recommended)
- **Storage**: 10GB volume = $1/GB/month = $10
- **Compute**: $20/month for dedicated resources
- **Database**: Postgres 8GB = $15/month
- **Total**: ~$45/month

---

## Summary

1. ✅ Create Railway volume: `/data` (10GB)
2. ✅ Upload ZIP to volume: `/data/medicaid_claims.zip`
3. ✅ Deploy 3 services: API, Worker, Beat
4. ✅ Start loading via API: `POST /api/v1/data-loading/start`
5. ✅ Monitor progress: `GET /api/v1/data-loading/progress`
6. ✅ Resume if crashed: `POST /api/v1/data-loading/resume`

**Estimated Time**: 2-4 hours on Railway Pro, 4-6 hours on Free tier

**Need Help?** Check Railway logs: `railway logs --service worker --follow`
