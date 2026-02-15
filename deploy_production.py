#!/usr/bin/env python3
"""
PRODUCTION DEPLOYMENT SCRIPT
Remove ALL mock data and synthetic fallbacks.
Enables real 77M claims fraud detection.
"""

import os
import re
import sys
from pathlib import Path

# Configuration
BACKEND_DIR = Path("backend")
DETECTOR_FILES = [
    "analytics/sadc_detector.py",
    "analytics/cdpap_detector.py", 
    "analytics/nemt_detector.py",
    "analytics/pharmacy_detector.py",
    "analytics/recipient_detector.py",
    "analytics/patterns.py"
]

ROUTE_FILES = [
    "routes/analytics_trigger.py",
    "routes/graph.py",
    "routes/homecare.py"
]

def remove_mock_generators():
    """Remove all _generate_mock_* methods from detector files."""
    print("\n🔧 REMOVING MOCK DATA GENERATORS...")
    
    for detector_file in DETECTOR_FILES:
        path = BACKEND_DIR / detector_file
        if not path.exists():
            print(f"⚠️  Skipped (not found): {detector_file}")
            continue
        
        with open(path, 'r') as f:
            content = f.read()
        
        # Count mock methods before
        mock_count = len(re.findall(r'def _generate_mock_', content))
        
        # Remove all _generate_mock_* method definitions
        # This regex matches from "def _generate_mock_" to the next "def " or end of file
        original_len = len(content)
        content = re.sub(
            r'\n\s*def _generate_mock_.*?(?=\n    def |\nclass |\Z)',
            '',
            content,
            flags=re.DOTALL
        )
        
        if original_len != len(content):
            with open(path, 'w') as f:
                f.write(content)
            print(f"✅ {detector_file}: Removed {mock_count} mock methods")
        else:
            print(f"ⓘ  {detector_file}: No mock methods found")

def remove_mock_fallbacks():
    """Remove try/except blocks that return mock data."""
    print("\n🔧 REMOVING MOCK FALLBACK LOGIC...")
    
    all_files = DETECTOR_FILES + ROUTE_FILES
    
    for file in all_files:
        path = BACKEND_DIR / file
        if not path.exists():
            continue
        
        with open(path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Replace except blocks that return mock data
        # Pattern: except ... return ...mock...
        content = re.sub(
            r'except\s+.*?:\s*\n\s*(?:logger\.warning\(.*?\)\s*\n\s*)?return\s+.*?(?:_generate_mock|MockData|MOCK)',
            'except Exception as e:\n            logger.error(f"Database query failed: {e}")\n            raise',
            content,
            flags=re.DOTALL
        )
        
        if original_content != content:
            with open(path, 'w') as f:
                f.write(content)
            print(f"✅ Updated: {file}")

def remove_demo_mode_flags():
    """Remove DEMO mode checks and mock data interceptors."""
    print("\n🔧 REMOVING DEMO MODE FLAGS...")
    
    files_to_check = [
        "backend/main.py",
        "backend/database.py",
        "frontend/src/services/api.ts",
        "frontend/src/pages/UnifiedDashboard.tsx"
    ]
    
    for file in files_to_check:
        path = Path(file)
        if not path.exists():
            continue
        
        with open(path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Remove DEMO_MODE conditionals
        content = re.sub(r'if\s+.*?DEMO.*?:\s*\n.*?(?=\n\s{0,4}[^\ ]|\Z)', '', content, flags=re.DOTALL)
        
        # Remove "using mock data" warning logs
        content = re.sub(r'.*?using mock data.*?\n', '', content, flags=re.IGNORECASE)
        
        # Remove synthetic data markers
        content = re.sub(r'.*?#.*?SYNTHETIC.*?\n', '', content, flags=re.IGNORECASE)
        
        if original_content != content:
            with open(path, 'w') as f:
                f.write(content)
            print(f"✅ Cleaned: {file}")

def create_production_verification():
    """Create script to verify real data is in production."""
    print("\n📝 CREATING VERIFICATION SCRIPT...")
    
    script_content = '''#!/usr/bin/env python3
"""
Verify production data is live and real.
77.3M claims, 318.7K providers must be present.
"""

import sys
from sqlalchemy import create_engine, text
from backend.config import settings

def verify_production():
    print("🔍 VERIFYING PRODUCTION DATA...")
    
    engine = create_engine(settings.database_dsn, echo=False)
    
    try:
        with engine.connect() as conn:
            # Check claims
            result = conn.execute(text("SELECT COUNT(*) FROM claims"))
            claims = result.scalar()
            print(f"📊 Total Claims: {claims:,}")
            
            if claims < 70_000_000:
                print(f"❌ CRITICAL: Only {claims:,} claims (expected 77.3M)")
                return False
            
            # Check providers
            result = conn.execute(text("SELECT COUNT(*) FROM providers"))
            providers = result.scalar()
            print(f"🏥 Total Providers: {providers:,}")
            
            # Check for high-value claims
            result = conn.execute(text("""
                SELECT COUNT(*), AVG(amount)
                FROM claims WHERE amount > 100000
            """))
            high_value, avg_high = result.fetchone()
            print(f"💰 High-Value Claims (>$100K): {high_value:,} (avg: ${avg_high:,.0f})")
            
            # Sample real provider
            result = conn.execute(text("""
                SELECT name FROM providers LIMIT 1
            """))
            real_name = result.scalar()
            print(f"✅ Real Provider Example: {real_name}")
            
            print("\\n✅✅✅ PRODUCTION DATA VERIFIED ✅✅✅")
            print("System is using REAL 77.3M claims for fraud detection.")
            return True
            
    except Exception as e:
        print(f"❌ VERIFICATION FAILED: {e}")
        print("Check DATABASE_URL and ensure PostgreSQL is running.")
        return False

if __name__ == "__main__":
    success = verify_production()
    sys.exit(0 if success else 1)
'''
    
    verify_path = BACKEND_DIR / "scripts" / "verify_production.py"
    verify_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(verify_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(verify_path, 0o755)
    print(f"✅ Created: {verify_path}")

def create_env_template():
    """Create .env.production template."""
    print("\n📝 CREATING PRODUCTION ENV TEMPLATE...")
    
    env_content = '''# PRODUCTION ENVIRONMENT
# Copy to .env and update with real values

# Mode
ENVIRONMENT=production
DEBUG=false

# Database - UPDATE WITH YOUR REAL DATABASE
DATABASE_URL=postgresql://analyst:CHANGE_ME@localhost:5432/medicaid_db
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20

# Data Source (must have 77.3M claims loaded)
MEDICAID_DATASET_PATH=/data/medicaid_claims.parquet

# Application
HOST=0.0.0.0
PORT=8000
SECRET_KEY=change_this_to_random_string_in_production
WORKERS=4

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Logging
LOG_LEVEL=INFO

# Cache
ENABLE_POL_CACHE=true
POL_CACHE_DAYS=7

# LLM (optional)
LLM_PROVIDER=local
# OPENAI_API_KEY=sk-...
# CLAUDE_API_KEY=sk-...

# Exports
EXPORT_DIR=/app/exports

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_MODE=production
'''
    
    env_path = Path(".env.production")
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created: {env_path}")
    print("   ⚠️  UPDATE DATABASE_URL WITH REAL CREDENTIALS")

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     PRODUCTION DEPLOYMENT - REMOVE ALL MOCK DATA           ║")
    print("║        Enabling Real 77.3M Claims Fraud Detection           ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Step 1: Remove mock generators
    remove_mock_generators()
    
    # Step 2: Remove mock fallback logic
    remove_mock_fallbacks()
    
    # Step 3: Remove demo mode
    remove_demo_mode_flags()
    
    # Step 4: Create verification script
    create_production_verification()
    
    # Step 5: Create env template
    create_env_template()
    
    print("\n" + "="*60)
    print("✅ PRODUCTION SETUP COMPLETE")
    print("="*60)
    
    print("\nNEXT STEPS:")
    print("1. Update .env.production with real database credentials")
    print("2. Run: python backend/scripts/verify_production.py")
    print("3. Start backend: uvicorn backend.main:app --host 0.0.0.0 --port 8000")
    print("4. Start frontend: cd frontend && npm start")
    print("5. Open http://localhost:3000 - should show REAL data now!")
    
    print("\nVERIFICATION:")
    print("- Dashboard shows real provider names (not 'Provider 12345')")
    print("- Fraud Rings shows real provider networks")
    print("- Providers tab searches real database")
    print("- No 'using mock data' messages in logs")

if __name__ == "__main__":
    main()
