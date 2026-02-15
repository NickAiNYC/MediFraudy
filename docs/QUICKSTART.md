# Quick Start Guide

## Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL 14+

## Backend Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Run migrations:
```bash
alembic upgrade head
```

4. Start the server:
```bash
uvicorn main:app --reload
```

## Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start development server:
```bash
npm run dev
```

## First Steps

1. Access the dashboard at http://localhost:5173
2. Navigate to "Fraud Rings" to see the graph visualization
3. Use the "Generate Report" button to export findings
