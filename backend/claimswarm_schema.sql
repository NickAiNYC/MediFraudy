-- ClaimSwarm Database Schema
-- Autonomous claims processing and fraud detection

-- Claim results table
CREATE TABLE IF NOT EXISTS claim_results (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(255) UNIQUE NOT NULL,
    complexity VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    fraud_score DECIMAL(5,4) NOT NULL,
    estimated_cost DECIMAL(12,2) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    suspicious_patterns JSONB,
    evidence_links JSONB,
    recommendation VARCHAR(100) NOT NULL,
    processing_time DECIMAL(8,3) NOT NULL,
    blockchain_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim investigation details
CREATE TABLE IF NOT EXISTS claim_investigations (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(255) REFERENCES claim_results(claim_id) ON DELETE CASCADE,
    fraud_indicators JSONB,
    suspicious_patterns JSONB,
    entity_connections JSONB,
    risk_score DECIMAL(5,4) NOT NULL,
    investigation_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim estimation details
CREATE TABLE IF NOT EXISTS claim_estimations (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(255) REFERENCES claim_results(claim_id) ON DELETE CASCADE,
    damage_assessment JSONB,
    cost_breakdown JSONB,
    confidence_score DECIMAL(5,4) NOT NULL,
    estimated_total DECIMAL(12,2) NOT NULL,
    recommended_settlement DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ClaimSwarm configuration
CREATE TABLE IF NOT EXISTS claimswarm_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fraud graph entities
CREATE TABLE IF NOT EXISTS fraud_graph_entities (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_value VARCHAR(255) NOT NULL,
    claim_count INTEGER DEFAULT 1,
    risk_score DECIMAL(5,4) DEFAULT 0.0,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_value)
);

-- Fraud graph connections
CREATE TABLE IF NOT EXISTS fraud_graph_connections (
    id SERIAL PRIMARY KEY,
    entity1_id INTEGER REFERENCES fraud_graph_entities(id) ON DELETE CASCADE,
    entity2_id INTEGER REFERENCES fraud_graph_entities(id) ON DELETE CASCADE,
    connection_weight INTEGER DEFAULT 1,
    connection_type VARCHAR(50),
    first_claim_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity1_id, entity2_id)
);

-- Claim processing queue
CREATE TABLE IF NOT EXISTS claim_processing_queue (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(255) UNIQUE NOT NULL,
    claim_data JSONB NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(20) DEFAULT 'pending',
    job_id VARCHAR(255),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_claim_results_claim_id ON claim_results(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_results_status ON claim_results(status);
CREATE INDEX IF NOT EXISTS idx_claim_results_created_at ON claim_results(created_at);
CREATE INDEX IF NOT EXISTS idx_claim_results_fraud_score ON claim_results(fraud_score);

CREATE INDEX IF NOT EXISTS idx_claim_investigations_claim_id ON claim_investigations(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_estimations_claim_id ON claim_estimations(claim_id);

CREATE INDEX IF NOT EXISTS idx_fraud_entities_type ON fraud_graph_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_fraud_entities_risk_score ON fraud_graph_entities(risk_score);

CREATE INDEX IF NOT EXISTS idx_fraud_connections_entity1 ON fraud_graph_connections(entity1_id);
CREATE INDEX IF NOT EXISTS idx_fraud_connections_entity2 ON fraud_graph_connections(entity2_id);
CREATE INDEX IF NOT EXISTS idx_fraud_connections_weight ON fraud_graph_connections(connection_weight);

CREATE INDEX IF NOT EXISTS idx_claim_queue_status ON claim_processing_queue(status);
CREATE INDEX IF NOT EXISTS idx_claim_queue_priority ON claim_processing_queue(priority);
CREATE INDEX IF NOT EXISTS idx_claim_queue_submitted_at ON claim_processing_queue(submitted_at);

-- Insert default configuration
INSERT INTO claimswarm_config (config_key, config_value, description) VALUES
('approval_threshold_simple', '0.3', 'Auto-approval threshold for simple claims'),
('approval_threshold_moderate', '0.2', 'Auto-approval threshold for moderate claims'),
('approval_threshold_complex', '0.1', 'Auto-approval threshold for complex claims'),
('approval_threshold_critical', '0.05', 'Auto-approval threshold for critical claims'),
('max_processing_time', '300', 'Maximum processing time in seconds'),
('fraud_graph_min_connections', '3', 'Minimum connections for fraud ring detection'),
('batch_size', '100', 'Batch processing size'),
('enable_blockchain', 'true', 'Enable blockchain evidence storage')
ON CONFLICT (config_key) DO NOTHING;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_claim_results_updated_at BEFORE UPDATE ON claim_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_claim_investigations_updated_at BEFORE UPDATE ON claim_investigations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_claim_estimations_updated_at BEFORE UPDATE ON claim_estimations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fraud_entities_last_seen BEFORE UPDATE ON fraud_graph_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
