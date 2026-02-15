# ⚡ Performance Optimization Guide

## Query Performance Enhancements

### 1. Database Indexes (CRITICAL)

**Required indexes for optimal performance:**

```sql
-- Claims table indexes
CREATE INDEX idx_provider ON claims(provider_id);
CREATE INDEX idx_claim_date ON claims(claim_date);
CREATE INDEX idx_beneficiary ON claims(beneficiary_id);
CREATE INDEX idx_aide ON claims(aide_id);
CREATE INDEX idx_provider_claim ON claims(provider_id, claim_date); -- Composite for range queries
CREATE INDEX idx_billing_code ON claims(billing_code);

-- EVV Records indexes
CREATE INDEX idx_claim ON evv_records(claim_id);
CREATE INDEX idx_evv_claim ON evv_records(claim_id, was_manually_adjusted); -- Composite
CREATE INDEX idx_adjusted ON evv_records(was_manually_adjusted);

-- Hospital Admissions indexes
CREATE INDEX idx_beneficiary ON hospital_admissions(beneficiary_id);
CREATE INDEX idx_dates ON hospital_admissions(admission_date, discharge_date);
CREATE INDEX idx_admission ON hospital_admissions(beneficiary_id, admission_date); -- Composite

-- Aides indexes
CREATE INDEX idx_aide ON aides(id);
CREATE INDEX idx_provider ON aides(provider_id);

-- Aide Time Off indexes
CREATE INDEX idx_aide ON aide_time_off(aide_id);
CREATE INDEX idx_dates ON aide_time_off(start_date, end_date);
CREATE INDEX idx_aide_dates ON aide_time_off(aide_id, start_date, end_date); -- Composite

-- Recruiters indexes
CREATE INDEX idx_recruiter ON recruiter_assignments(recruiter_id);
CREATE INDEX idx_beneficiary ON recruiter_assignments(beneficiary_id);
CREATE INDEX idx_recruitment_date ON recruiter_assignments(recruitment_date);
```

**Verify index usage:**

```sql
-- Check if indexes are being used
EXPLAIN SELECT * FROM claims c USE INDEX (idx_provider_claim)
WHERE c.provider_id = 123 AND c.claim_date >= '2023-01-01';

-- Should show "Using index" in Extra column
```

### 2. Pagination for Large Datasets

**All fraud detection methods now support pagination:**

```python
# EVV Fraud with pagination
results = detector.detect_evv_fraud(
    provider_id=123,
    lookback_days=730,
    limit=10000,      # Records per page
    offset=0          # Start position
)

# Process in batches
for page in range(0, 100000, 10000):
    batch = detector.detect_evv_fraud(
        provider_id=123,
        limit=10000,
        offset=page
    )
    # Process batch...
```

**API endpoint usage:**

```bash
# First page
curl "http://localhost:8000/api/homecare/evv-fraud/123?limit=1000&offset=0"

# Second page
curl "http://localhost:8000/api/homecare/evv-fraud/123?limit=1000&offset=1000"

# Third page
curl "http://localhost:8000/api/homecare/evv-fraud/123?limit=1000&offset=2000"
```

### 3. Configurable Thresholds

**Ghost Visit Detection - Adjust sensitivity:**

```python
# Strict: Flag even 1-minute overlaps
results = detector.detect_ghost_visits(
    provider_id=123,
    min_overlap_minutes=1
)

# Lenient: Only flag significant overlaps
results = detector.detect_ghost_visits(
    provider_id=123,
    min_overlap_minutes=15  # 15+ minute overlaps
)
```

**API endpoint:**

```bash
# Strict detection
curl "http://localhost:8000/api/homecare/ghost-visits/123?min_overlap_minutes=1"

# Lenient detection (faster, fewer false positives)
curl "http://localhost:8000/api/homecare/ghost-visits/123?min_overlap_minutes=30"
```

### 4. Query Optimization Strategies

**Index Hints** - Force MySQL to use specific indexes:

```sql
-- Already implemented in queries
FROM claims c USE INDEX (idx_provider, idx_claim_date)
JOIN evv_records e USE INDEX (idx_claim) ON c.claim_id = e.claim_id
```

**Ordering for Fast Access:**

```sql
-- Results ordered by most valuable violations first
ORDER BY c.amount DESC        -- Highest dollar amounts first
ORDER BY overlap_minutes DESC -- Worst overlaps first
ORDER BY days_hospitalized DESC -- Longest stays first
```

**Query Limits:**

```sql
-- All queries now include limits
LIMIT :limit OFFSET :offset
```

### 5. Database Configuration

**MySQL Configuration** (`/etc/mysql/my.cnf`):

```ini
[mysqld]
# Query Cache (if MySQL < 8.0)
query_cache_type = 1
query_cache_size = 256M

# Buffer Pool (critical for performance)
innodb_buffer_pool_size = 8G  # 70-80% of available RAM

# Connection Settings
max_connections = 200
thread_cache_size = 50

# InnoDB Settings
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 2
innodb_file_per_table = 1

# Temporary Tables
tmp_table_size = 256M
max_heap_table_size = 256M
```

**PostgreSQL Configuration** (`postgresql.conf`):

```ini
# Memory Settings
shared_buffers = 8GB          # 25% of RAM
effective_cache_size = 24GB   # 75% of RAM
work_mem = 256MB
maintenance_work_mem = 2GB

# Planner Settings
random_page_cost = 1.1        # For SSD storage
effective_io_concurrency = 200

# WAL Settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### 6. Caching Strategy

**Redis Cache for Frequent Queries:**

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def detect_evv_fraud_cached(provider_id: int, lookback_days: int = 730):
    """Cached version of EVV fraud detection."""
    cache_key = f"evv_fraud:{provider_id}:{lookback_days}"
    
    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Not in cache - compute
    detector = HomeCareFraudDetector(db)
    results = detector.detect_evv_fraud(provider_id, lookback_days)
    
    # Store in cache (expire after 1 hour)
    redis_client.setex(cache_key, 3600, json.dumps(results))
    
    return results
```

### 7. Parallel Processing

**Process Multiple Providers Concurrently:**

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

async def analyze_provider_batch(provider_ids: List[int]):
    """Analyze multiple providers in parallel."""
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(detector.generate_homecare_risk_score, pid)
            for pid in provider_ids
        ]
        
        results = [future.result() for future in futures]
    
    return results

# Usage
provider_ids = range(1, 1001)  # 1000 providers
results = await analyze_provider_batch(provider_ids)
```

### 8. Database Partitioning

**Partition large tables by date:**

```sql
-- Partition claims table by year
ALTER TABLE claims
PARTITION BY RANGE (YEAR(claim_date)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- Queries automatically use only relevant partitions
SELECT * FROM claims 
WHERE claim_date >= '2024-01-01'  -- Only scans p2024, p2025 partitions
```

### 9. Monitoring Query Performance

**Enable Slow Query Log:**

```sql
-- MySQL
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;  -- Log queries > 2 seconds
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow-queries.log';

-- Analyze slow queries
mysqldumpslow /var/log/mysql/slow-queries.log
```

**Query Profiling:**

```sql
-- Profile a specific query
SET profiling = 1;

SELECT ... FROM claims ... -- Your query

SHOW PROFILES;
SHOW PROFILE FOR QUERY 1;
```

### 10. Batch Processing Recommendations

**For Large-Scale Analysis:**

```python
# Process 10,000 providers in batches of 100
batch_size = 100
total_providers = 10000

for i in range(0, total_providers, batch_size):
    batch_ids = range(i, min(i + batch_size, total_providers))
    
    # Process batch
    results = []
    for provider_id in batch_ids:
        result = detector.generate_homecare_risk_score(provider_id)
        results.append(result)
    
    # Write results to file/database
    write_results(results)
    
    # Sleep to avoid overwhelming database
    time.sleep(1)
```

## Performance Benchmarks

### Expected Performance (with optimizations):

| Operation | Dataset Size | Time | Throughput |
|-----------|-------------|------|------------|
| EVV Fraud Detection | 100K claims | 2-3s | 33K-50K claims/s |
| Ghost Visit Detection | 50K aide-days | 1-2s | 25K-50K days/s |
| Comprehensive Analysis | 1 provider | 5-8s | - |
| Batch Analysis | 100 providers | 8-12min | 8-12 providers/min |

### Scaling Recommendations:

- **< 100 providers**: No special optimization needed
- **100-1,000 providers**: Enable caching, use pagination
- **1,000-10,000 providers**: Add database read replicas, batch processing
- **10,000+ providers**: Consider data warehouse (Snowflake, BigQuery), distributed processing

## Quick Performance Checklist

- [ ] All recommended indexes created
- [ ] Database config tuned for workload
- [ ] Pagination enabled for large queries
- [ ] Slow query log monitoring enabled
- [ ] Redis cache implemented (optional)
- [ ] Connection pooling configured
- [ ] Query timeout limits set
- [ ] Regular ANALYZE TABLE to update statistics

---

**With these optimizations, the system can analyze millions of claims efficiently!** ⚡
