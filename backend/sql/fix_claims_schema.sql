-- Fix claims table schema - add provider_id foreign key
-- Run this in Railway Postgres console

ALTER TABLE claims 
ADD COLUMN IF NOT EXISTS provider_id INTEGER REFERENCES providers(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_claims_provider_id ON claims(provider_id);

-- Verify the column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'claims' 
ORDER BY ordinal_position;
