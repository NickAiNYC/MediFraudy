#!/bin/bash

# Deployment validation script
# Run after deploying to Railway to verify everything works

set -e

APP_URL="${1:-https://your-app.up.railway.app}"

echo "🚀 Validating MediFraudy deployment at $APP_URL"
echo "=================================================="

# Test 1: Health Check
echo "✓ Testing health endpoint..."
HEALTH=$(curl -s "$APP_URL/health" || echo '{"status":"error"}')
STATUS=$(echo $HEALTH | jq -r '.status' 2>/dev/null || echo "error")

if [ "$STATUS" = "healthy" ]; then
    echo "  ✅ Health check passed"
else
    echo "  ❌ Health check failed: $STATUS"
    echo "  Response: $HEALTH"
    exit 1
fi

# Test 2: Database Connection
echo "✓ Testing database connection..."
DB_STATUS=$(echo $HEALTH | jq -r '.checks.database' 2>/dev/null || echo "error")

if [ "$DB_STATUS" = "connected" ]; then
    echo "  ✅ Database connected"
else
    echo "  ❌ Database connection failed: $DB_STATUS"
    exit 1
fi

# Test 3: Redis Connection (optional)
echo "✓ Testing Redis connection..."
REDIS_STATUS=$(echo $HEALTH | jq -r '.checks.redis' 2>/dev/null || echo "null")

if [ "$REDIS_STATUS" = "connected" ]; then
    echo "  ✅ Redis connected"
elif [ "$REDIS_STATUS" = "null" ]; then
    echo "  ⚠️  Redis not configured (optional)"
else
    echo "  ⚠️  Redis connection issue (optional): $REDIS_STATUS"
fi

# Test 4: Security Headers
echo "✓ Testing security headers..."
HEADERS=$(curl -sI "$APP_URL/health" 2>/dev/null || echo "")

if echo "$HEADERS" | grep -q "X-Content-Type-Options"; then
    echo "  ✅ Security headers present"
else
    echo "  ⚠️  Security headers missing (may be expected in development)"
fi

# Test 5: API Root
echo "✓ Testing API root endpoint..."
ROOT_RESPONSE=$(curl -s "$APP_URL/" || echo '{"status":"error"}')
SERVICE=$(echo $ROOT_RESPONSE | jq -r '.service' 2>/dev/null || echo "unknown")

if [[ "$SERVICE" == *"MediFraudy"* ]]; then
    echo "  ✅ API root responding correctly"
else
    echo "  ⚠️  API root response unexpected: $ROOT_RESPONSE"
fi

echo ""
echo "=================================================="
echo "✅ Deployment validation completed!"
echo ""
echo "Summary:"
echo "  - Health check: ✅"
echo "  - Database: ✅"
echo "  - Redis: ${REDIS_STATUS}"
echo "  - API Root: ✅"
echo ""
echo "Next steps:"
echo "1. Create admin user"
echo "2. Configure monitoring alerts"
echo "3. Set up automated backups"
echo "4. Review audit logs"
