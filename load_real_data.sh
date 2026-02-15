#!/bin/bash

# MediFraudy Real Data Loader - Quick Start
# Usage: ./load_real_data.sh [path_to_dataset] [state]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
STATE="${2:-NY}"
CHUNKSIZE="${3:-50000}"
CONTAINER="medicaid_backend"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      MediFraudy Real Data Loader - Quick Start             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if file provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: No data file provided${NC}"
    echo ""
    echo "Usage: $0 <path_to_dataset> [state] [chunksize]"
    echo ""
    echo "Examples:"
    echo "  $0 ./medicaid_claims.csv NY 50000"
    echo "  $0 /data/claims.parquet CA 100000"
    echo "  $0 claims.zip NY 25000"
    echo ""
    echo "Supported formats: CSV, Parquet, Excel, ZIP"
    exit 1
fi

# Verify file exists
if [ ! -f "$1" ]; then
    echo -e "${RED}❌ File not found: $1${NC}"
    exit 1
fi

FILE_PATH="$1"
FILE_NAME=$(basename "$FILE_PATH")
FILE_SIZE=$(du -h "$FILE_PATH" | cut -f1)

echo -e "${GREEN}✓ Dataset Information:${NC}"
echo "  File: $FILE_NAME"
echo "  Size: $FILE_SIZE"
echo "  State Filter: $STATE"
echo "  Chunk Size: $CHUNKSIZE rows"
echo ""

# Step 1: Check database connection
echo -e "${BLUE}[1/5] Checking database connection...${NC}"
if docker exec $CONTAINER psql postgresql://medicaid:medicaid@medicaid_postgres:5432/medicaid -c "SELECT 1" &>/dev/null; then
    echo -e "${GREEN}✓ Database connected${NC}"
else
    echo -e "${RED}❌ Cannot connect to database${NC}"
    echo "Make sure containers are running: docker compose up -d"
    exit 1
fi
echo ""

# Step 2: Copy data into container
echo -e "${BLUE}[2/5] Copying data to container...${NC}"
if docker cp "$FILE_PATH" $CONTAINER:/app/data_import/$FILE_NAME; then
    echo -e "${GREEN}✓ Data copied successfully${NC}"
else
    echo -e "${RED}❌ Failed to copy data${NC}"
    exit 1
fi
echo ""

# Step 3: Clear existing data (optional)
read -p "Clear existing data before loading? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}[3/5] Clearing existing data...${NC}"
    docker exec $CONTAINER python -c "
from database import SessionLocal, Base, engine
from models import Claim, Provider

print('Clearing tables...')
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print('✓ Tables cleared')
"
    echo -e "${GREEN}✓ Data cleared${NC}"
else
    echo -e "${YELLOW}⊘ Keeping existing data${NC}"
fi
echo ""

# Step 4: Load data
echo -e "${BLUE}[4/5] Loading real data (this may take a while)...${NC}"
docker exec $CONTAINER python scripts/load_data.py \
    --file /app/data_import/$FILE_NAME \
    --state $STATE \
    --chunksize $CHUNKSIZE

echo ""
echo -e "${GREEN}✓ Data loaded successfully${NC}"
echo ""

# Step 5: Verify and show stats
echo -e "${BLUE}[5/5] Verifying data load...${NC}"

PROVIDER_COUNT=$(docker exec $CONTAINER psql \
    postgresql://medicaid:medicaid@medicaid_postgres:5432/medicaid \
    -t -c "SELECT COUNT(*) FROM providers" 2>/dev/null | tr -d ' ')

CLAIM_COUNT=$(docker exec $CONTAINER psql \
    postgresql://medicaid:medicaid@medicaid_postgres:5432/medicaid \
    -t -c "SELECT COUNT(*) FROM claims" 2>/dev/null | tr -d ' ')

STATE_COUNT=$(docker exec $CONTAINER psql \
    postgresql://medicaid:medicaid@medicaid_postgres:5432/medicaid \
    -t -c "SELECT COUNT(DISTINCT state) FROM providers" 2>/dev/null | tr -d ' ')

echo -e "${GREEN}✓ Data verification complete:${NC}"
echo "  Providers: $PROVIDER_COUNT"
echo "  Claims: $CLAIM_COUNT"
echo "  States: $STATE_COUNT"
echo ""

# Step 6: Trigger analysis
read -p "Run fraud detection analysis now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Running fraud analysis...${NC}"
    docker exec $CONTAINER python scripts/run_analysis.py --state $STATE
    echo -e "${GREEN}✓ Analysis complete${NC}"
fi
echo ""

# Final message
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ REAL DATA ACTIVATED!                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Your dashboard now has REAL data!"
echo ""
echo "Next steps:"
echo "  1. Open: http://localhost:3000"
echo "  2. Go to 'Fraud Rings' tab for network analysis"
echo "  3. Go to 'Providers' tab to search real facilities"
echo "  4. Go to 'Pattern Analysis' for POL forensics"
echo ""
echo "To monitor the dashboard updates:"
echo "  curl http://localhost:8000/api/analytics/dashboard/summary | jq"
echo ""
