-- Initialize database with extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET TIMEZONE='America/New_York';

-- Create indexes for performance
-- Tables are created by the application, so we cannot create indexes here yet.
-- These should be managed by Alembic migrations or created after app startup.
-- CREATE INDEX IF NOT EXISTS idx_claims_provider_date ON claims(provider_id, claim_date);
-- CREATE INDEX IF NOT EXISTS idx_claims_beneficiary ON claims(beneficiary_id);
-- CREATE INDEX IF NOT EXISTS idx_claims_code ON claims(billing_code);
-- CREATE INDEX IF NOT EXISTS idx_providers_type_state ON providers(facility_type, state);
