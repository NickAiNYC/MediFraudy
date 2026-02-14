-- Initialize database with extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET TIMEZONE='America/New_York';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_claims_provider_date ON claims(provider_id, claim_date);
CREATE INDEX IF NOT EXISTS idx_claims_beneficiary ON claims(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_claims_code ON claims(billing_code);
CREATE INDEX IF NOT EXISTS idx_providers_type_state ON providers(facility_type, state);
