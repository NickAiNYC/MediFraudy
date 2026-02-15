#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        MEDFRAUDY - GO LIVE WITH REAL 77.3M CLAIMS         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Clean mock data
echo "🔧 Step 1: Removing all mock data and synthetic fallbacks..."
python3 deploy_production.py

if [ $? -ne 0 ]; then
    echo "❌ Deploy script failed"
    exit 1
fi

echo ""
echo "🔍 Step 2: Verifying production database..."
python3 backend/scripts/verify_production.py

if [ $? -ne 0 ]; then
    echo "❌ Verification failed - database issue"
    exit 1
fi

echo ""
echo "✅ PRODUCTION READY"
echo ""
echo "START SERVICES:"
echo "  Terminal 1: uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo "  Terminal 2: cd frontend && npm start"
echo ""
echo "OPEN DASHBOARD: http://localhost:3000"
echo ""
echo "VERIFY REAL DATA:"
echo "  • Fraud Rings tab shows real networks"
echo "  • Providers tab searches 318K real providers"
echo "  • Pattern Analysis shows real POL violations"
echo "  • Home Care tab shows real EVV issues"
echo ""
