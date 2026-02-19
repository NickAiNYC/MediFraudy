#!/bin/bash
# MediFraudy Railway Deployment Automation Script
# Run this to deploy everything in one command

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     MediFraudy Railway Deployment - Automated Setup       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI not found${NC}"
    echo "Install it: npm install -g @railway/cli"
    exit 1
fi

echo -e "${GREEN}✓ Railway CLI found${NC}"

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Railway${NC}"
    echo "Logging in..."
    railway login
fi

echo -e "${GREEN}✓ Logged in to Railway${NC}"
echo ""

# Step 1: Initialize project
echo -e "${BLUE}[1/8] Initializing Railway project...${NC}"
if [ ! -f ".railway" ]; then
    railway init
else
    echo -e "${GREEN}✓ Project already initialized${NC}"
fi

# Step 2: Add PostgreSQL
echo -e "${BLUE}[2/8] Adding PostgreSQL database...${NC}"
railway add --database postgresql || echo -e "${YELLOW}⚠️  PostgreSQL may already exist${NC}"

# Step 3: Add Redis
echo -e "${BLUE}[3/8] Adding Redis...${NC}"
railway add --database redis || echo -e "${YELLOW}⚠️  Redis may already exist${NC}"

# Step 4: Create volume
echo -e "${BLUE}[4/8] Creating data volume...${NC}"
railway volume create data-volume --mount-path /data || echo -e "${YELLOW}⚠️  Volume may already exist${NC}"

# Step 5: Generate secrets
echo -e "${BLUE}[5/8] Generating security keys...${NC}"
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "GENERATE_MANUALLY")

echo -e "${GREEN}✓ Keys generated${NC}"

# Step 6: Set environment variables
echo -e "${BLUE}[6/8] Setting environment variables...${NC}"

railway variables set SECRET_KEY="$SECRET_KEY"
railway variables set JWT_SECRET_KEY="$JWT_SECRET_KEY"
railway variables set ENCRYPTION_KEY="$ENCRYPTION_KEY"
railway variables set ENVIRONMENT="production"
railway variables set DEBUG="False"
railway variables set MEDICAID_DATASET_PATH="/data/medicaid_claims.zip"
railway variables set CHUNK_SIZE="10000"
railway variables set DB_POOL_SIZE="10"
railway variables set DB_MAX_OVERFLOW="5"

echo -e "${GREEN}✓ Environment variables set${NC}"

# Step 7: Deploy
echo -e "${BLUE}[7/8] Deploying to Railway...${NC}"
git add .
git commit -m "Deploy to Railway" || echo "No changes to commit"
railway up

echo -e "${GREEN}✓ Deployment initiated${NC}"

# Step 8: Get URL
echo -e "${BLUE}[8/8] Getting deployment URL...${NC}"
sleep 5
RAILWAY_URL=$(railway domain 2>/dev/null || echo "Check Railway dashboard for URL")

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ DEPLOYMENT COMPLETE!                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Your MediFraudy API is deploying at:${NC}"
echo -e "${GREEN}$RAILWAY_URL${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Wait 2-3 minutes for deployment to complete"
echo "2. Check health: curl $RAILWAY_URL/health"
echo "3. Upload data file to /data/medicaid_claims.zip"
echo "4. Create admin user (see DEPLOY_TOMORROW.md)"
echo "5. Start data loading via API"
echo ""
echo -e "${BLUE}Monitor deployment:${NC}"
echo "  railway logs --follow"
echo ""
echo -e "${BLUE}View dashboard:${NC}"
echo "  railway open"
echo ""
echo -e "${GREEN}✓ Setup complete! See DEPLOY_TOMORROW.md for detailed next steps.${NC}"
