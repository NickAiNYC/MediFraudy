# 🔧 Fix Database Schema Mismatch

## 🔍 The Problem

Error: `column claims.provider_id does not exist`

Your database was created with NPI-based columns (`billing_provider_npi`) but your SQLAlchemy models expect a `provider_id` foreign key.

---

## ✅ Quick Fix (Run This Command)

### **On Railway:**

```bash
railway run --service mediFraudy-api python backend/scripts/fix_schema.py
```

### **Locally:**

```bash
cd backend
python scripts/fix_schema.py
```

---

## 🎯 What This Script Does

1. **Checks** if `provider_id` column exists in claims table
2. **Adds** the column if missing
3. **Populates** it by mapping NPIs to provider IDs
4. **Creates** foreign key constraint
5. **Adds** index for performance
6. **Verifies** the schema works

---

## 📊 Expected Output

```
🔧 Starting schema fix...
Existing claims columns: {'id', 'billing_provider_npi', 'amount', 'claim_date', ...}
Adding provider_id column to claims table...
✅ Added provider_id column
Populating provider_id from billing_provider_npi...
✅ Updated 1,234,567 claims with provider_id
Adding foreign key constraint...
✅ Added foreign key constraint
Creating index on provider_id...
✅ Created index
Claims with provider_id: 1,234,567 / 1,234,567
✅ Join query works correctly
🎉 Schema fix complete!
```

---

## 🚨 If You Have No Data Yet

If your database is empty (no claims loaded), the schema will be created correctly when you load data. Just make sure to use the Railway data loader which properly creates the `provider_id` relationship.

---

## 🔄 Alternative: Recreate Tables

If you haven't loaded real data yet, you can recreate the tables:

### **WARNING: This deletes all data!**

```bash
# On Railway
railway run --service mediFraudy-api python -c "
from database import Base, engine
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
print('✅ Tables recreated')
"
```

---

## 🧪 Verify After Fix

Test that queries work:

```bash
railway run --service mediFraudy-api python -c "
from database import get_db
from models import Provider, Claim
from sqlalchemy import func

db = next(get_db())
result = db.query(
    Provider.name,
    func.count(Claim.id).label('claim_count')
).join(Claim).group_by(Provider.id).limit(5).all()

for name, count in result:
    print(f'{name}: {count} claims')
"
```

---

## 📋 Next Steps

1. **Run the fix script** (see command above)
2. **Verify** the output shows success
3. **Test** your API endpoints
4. **Load data** if you haven't already

---

## 🎯 Root Cause

Your database tables were created from an older schema or manually, while your models.py expects:

```python
class Claim(Base):
    provider_id = Column(Integer, ForeignKey("providers.id"))
```

The fix script aligns the database with your current models.
