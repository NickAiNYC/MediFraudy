#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit
}

# Set up trap to catch Ctrl+C and kill both processes
trap cleanup SIGINT

echo "🚀 Starting MediFraudy Local Development Environment"
echo "==================================================="

# 1. Start Database (using Docker)
echo "Checking Database..."
# Set local DB connection string (localhost instead of postgres container name)
export DATABASE_URL="postgresql://analyst:changeme_in_production@localhost:5432/medicaid_db"

if ! docker ps | grep -q medicaid_postgres; then
    echo "📦 Starting Postgres container..."
    docker-compose up -d postgres
    echo "⏳ Waiting for Database to be ready..."
    sleep 5
else
    echo "✅ Database is running"
fi

# 2. Start Backend
echo "Starting Backend (FastAPI)..."
cd backend
source venv/bin/activate
# Install any missing requirements quietly
pip install -q -r requirements.txt
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "✅ Backend started with PID $BACKEND_PID"

# 3. Start Frontend
echo "Starting Frontend (React)..."
cd ../frontend
# Install missing node modules if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi
npm start &
FRONTEND_PID=$!
echo "✅ Frontend started with PID $FRONTEND_PID"

echo "==================================================="
echo "Backend: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both servers"
echo "==================================================="

# Wait for both processes
wait
