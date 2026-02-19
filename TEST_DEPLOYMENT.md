# 🧪 Testing Your Railway Deployment

## ✅ Your API is Running Successfully

Based on the logs:
```
✅ Database connection successful
✅ Database tables verified/created
🚀 MediFraudy API started successfully
INFO: Uvicorn running on http://0.0.0.0:8080
```

Your backend is **live and working**!

---

## 🌐 How to Access Your API

### **Get Your Public URL**

In Railway dashboard:
1. Click on **mediFraudy-api** service
2. Go to **Settings** tab
3. Look for **Public Networking** section
4. You'll see a URL like: `https://medifraudy-api-production.up.railway.app`

Or run this command:
```bash
railway status --service mediFraudy-api
```

---

## 🧪 Test Endpoints

### **1. Health Check (Simplest)**
```bash
# Replace with your actual Railway URL
curl https://medifraudy-api-production.up.railway.app/ping
```

**Expected response:**
```json
{
  "ping": "pong",
  "timestamp": 1708142037.851
}
```

### **2. Detailed Health Check**
```bash
curl https://medifraudy-api-production.up.railway.app/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-02-17T04:53:58.124878"
}
```

### **3. API Documentation**
Open in browser:
```
https://medifraudy-api-production.up.railway.app/docs
```

This shows all available endpoints with interactive testing.

### **4. Test Data Loading Status**
```bash
curl https://medifraudy-api-production.up.railway.app/api/v1/data-loading/stats
```

### **5. Test Provider Search**
```bash
curl "https://medifraudy-api-production.up.railway.app/api/providers?limit=5"
```

---

## ❌ Why `localhost:8080` Doesn't Work

When you run `railway run --service mediFraudy-api /bin/bash`, you're opening a shell **inside** the Railway container. The container doesn't expose ports to its own localhost - it only exposes them to Railway's public network.

**Wrong:**
```bash
curl http://localhost:8080/ping  # ❌ Won't work inside container
```

**Right:**
```bash
# From your local machine:
curl https://your-railway-url.railway.app/ping  # ✅ Works
```

---

## 🔍 Get Your Railway URL

### **Method 1: Railway CLI**
```bash
railway status --service mediFraudy-api
```

Look for the "Deployments" section with the public URL.

### **Method 2: Railway Dashboard**
1. Open https://railway.app/dashboard
2. Select your project "MediFraudy"
3. Click "mediFraudy-api" service
4. Look for the URL in the top right or Settings → Networking

### **Method 3: Environment Variable**
```bash
railway variables --service mediFraudy-api | grep RAILWAY_PUBLIC_DOMAIN
```

---

## 🎯 Quick Test Script

Save this as `test_api.sh`:

```bash
#!/bin/bash

# Get Railway URL (replace with your actual URL)
API_URL="https://medifraudy-api-production.up.railway.app"

echo "🧪 Testing MediFraudy API..."
echo ""

echo "1️⃣ Testing /ping..."
curl -s "$API_URL/ping" | jq .
echo ""

echo "2️⃣ Testing /health..."
curl -s "$API_URL/health" | jq .
echo ""

echo "3️⃣ Testing /api/v1/data-loading/stats..."
curl -s "$API_URL/api/v1/data-loading/stats" | jq .
echo ""

echo "4️⃣ Testing /api/providers..."
curl -s "$API_URL/api/providers?limit=3" | jq .
echo ""

echo "✅ All tests complete!"
```

Run it:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## 🚀 Next Steps

### **1. Find Your Railway URL**
```bash
railway status --service mediFraudy-api
```

### **2. Test the API**
```bash
curl https://YOUR-URL.railway.app/ping
```

### **3. Open API Docs**
```
https://YOUR-URL.railway.app/docs
```

### **4. Update Frontend**
In your frontend `.env` or Railway frontend variables:
```bash
REACT_APP_API_URL=https://YOUR-BACKEND-URL.railway.app
```

---

## 📊 Available Endpoints

Once you have your URL, these endpoints are ready:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ping` | GET | Simple health check |
| `/health` | GET | Detailed health status |
| `/docs` | GET | Interactive API documentation |
| `/api/providers` | GET | Search providers |
| `/api/anomalies` | GET | List anomalies |
| `/api/alerts` | GET | Real-time fraud alerts |
| `/api/v1/data-loading/stats` | GET | Data loading statistics |
| `/api/v1/data-loading/progress` | GET | Current loading progress |
| `/api/v1/agent/chat` | POST | DeepSeek AI chat |
| `/api/analytics/dashboard/summary` | GET | Dashboard summary |

---

## 🐛 Troubleshooting

### **Issue: "Failed to connect"**
- ✅ Make sure you're using the **public Railway URL**, not localhost
- ✅ Check that the service is deployed (green status in Railway dashboard)

### **Issue: "404 Not Found"**
- ✅ Verify the endpoint path is correct (check `/docs`)
- ✅ Make sure you're using the backend URL, not frontend URL

### **Issue: "Connection refused"**
- ✅ Service might be redeploying - wait 30 seconds and try again
- ✅ Check Railway logs: `railway logs --service mediFraudy-api`

---

## ✅ Your API is Working!

The logs show everything is running perfectly:
- ✅ Database connected
- ✅ Tables created
- ✅ Server running on port 8080
- ✅ Ready to accept requests

Just use the **public Railway URL** instead of localhost! 🚀
