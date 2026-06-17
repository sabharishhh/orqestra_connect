-- schema.sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. SYSTEMS (Tracks registered AI agents/microservices)
CREATE TABLE systems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    api_key_hash VARCHAR(255),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. OUTPUT SAMPLES (The raw text payloads from the agents)
CREATE TABLE output_samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    system_id UUID REFERENCES systems(id) ON DELETE CASCADE,
    raw_text TEXT NOT NULL,
    processing_status VARCHAR(50) DEFAULT 'PENDING',
    token_cost NUMERIC(10, 6) DEFAULT 0.0,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. ENTITIES (Canonical medical/business concepts, e.g., "Metformin", "eGFR")
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_name VARCHAR(255) UNIQUE NOT NULL,
    domain VARCHAR(100),
    variance_score NUMERIC(5, 4) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. INDUCTION CANDIDATES (Unmapped concepts waiting for human approval)
CREATE TABLE induction_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposed_name VARCHAR(255) NOT NULL,
    claim_frequency INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. CLAIMS (The atomic SPO extracted rules with their vector embeddings)
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    system_id UUID REFERENCES systems(id) ON DELETE CASCADE,
    sample_id UUID REFERENCES output_samples(id) ON DELETE SET NULL,
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    clinical_context TEXT,
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. CONTRADICTIONS (The collisions caught by the Bouncer/Apex)
CREATE TABLE contradictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_a_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    claim_b_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    severity VARCHAR(50) NOT NULL,
    confidence_score NUMERIC(5, 4) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 7. EXPLANATIONS (The AI-generated reasoning for the collision)
CREATE TABLE explanations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contradiction_id UUID UNIQUE REFERENCES contradictions(id) ON DELETE CASCADE,
    why_they_contradict TEXT NOT NULL,
    likely_stale_system UUID REFERENCES systems(id) ON DELETE SET NULL,
    risk_level VARCHAR(50),
    recommended_action TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. COHERENCE SCORES (The overall health score of the enterprise)
CREATE TABLE coherence_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    system_id UUID REFERENCES systems(id) ON DELETE CASCADE,
    score NUMERIC(5, 4) NOT NULL,
    total_estimated_cost_risk NUMERIC(15, 2) DEFAULT 0.0,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. COST METRICS (Tracking token expenditure for ROI dashboard)
CREATE TABLE cost_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    system_id UUID REFERENCES systems(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost_usd NUMERIC(10, 6) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. ALERT RULES (Configured Slack/Email alerts)
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    system_id UUID REFERENCES systems(id) ON DELETE CASCADE,
    severity_threshold VARCHAR(50) NOT NULL,
    slack_channel VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

-- 11. ALERT EVENTS (Log of dispatched alerts)
CREATE TABLE alert_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID REFERENCES alert_rules(id) ON DELETE CASCADE,
    contradiction_id UUID REFERENCES contradictions(id) ON DELETE CASCADE,
    dispatched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create IVFFlat Index for fast vector similarity searches
CREATE INDEX ON claims USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);