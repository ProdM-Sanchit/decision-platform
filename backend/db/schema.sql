-- Horizontal Decision Platform - Database Schema
-- PostgreSQL 15+
-- Version: 1.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Cases: Single source of truth for decision processes
CREATE TABLE cases (
    case_id VARCHAR(50) PRIMARY KEY DEFAULT ('case_' || uuid_generate_v4()::text),
    vertical VARCHAR(50) NOT NULL,
    status VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    sla_deadline TIMESTAMP,
    policy_version VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT chk_valid_status CHECK (
        status IN (
            'draft', 'submitted', 'processing',
            'under_review', 'under_review.identity_check', 'under_review.fraud_check',
            'under_review.compliance_check', 'under_review.manual_review',
            'approved', 'rejected', 'needs_more_info', 'expired'
        )
    )
);

CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_created_at ON cases(created_at);
CREATE INDEX idx_cases_sla_deadline ON cases(sla_deadline) WHERE sla_deadline IS NOT NULL;
CREATE INDEX idx_cases_customer_id ON cases(customer_id);
CREATE INDEX idx_cases_vertical ON cases(vertical);

-- Documents: Uploaded files associated with cases
CREATE TABLE documents (
    document_id VARCHAR(50) PRIMARY KEY DEFAULT ('doc_' || uuid_generate_v4()::text),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    document_subtype VARCHAR(50),
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    ocr_status VARCHAR(20) DEFAULT 'pending' CHECK (ocr_status IN ('pending', 'processing', 'completed', 'failed')),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_documents_case_id ON documents(case_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_ocr_status ON documents(ocr_status);

-- Evidence: Extracted and normalized information from documents/APIs
CREATE TABLE evidence (
    evidence_id VARCHAR(50) PRIMARY KEY DEFAULT ('evd_' || uuid_generate_v4()::text),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    data JSONB NOT NULL,
    
    UNIQUE(case_id, evidence_type, version)
);

CREATE INDEX idx_evidence_case_id ON evidence(case_id);
CREATE INDEX idx_evidence_type ON evidence(evidence_type);
CREATE INDEX idx_evidence_created_at ON evidence(created_at);

-- Agent Recommendations: Outputs from individual agents
CREATE TABLE agent_recommendations (
    recommendation_id VARCHAR(50) PRIMARY KEY DEFAULT ('rec_' || uuid_generate_v4()::text),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    agent_name VARCHAR(50) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    recommendation JSONB NOT NULL,
    processing_time_ms INTEGER,
    
    CONSTRAINT chk_recommendation_structure CHECK (
        recommendation ? 'action' AND
        recommendation ? 'confidence' AND
        recommendation ? 'reasoning'
    )
);

CREATE INDEX idx_agent_recs_case_id ON agent_recommendations(case_id);
CREATE INDEX idx_agent_recs_agent_name ON agent_recommendations(agent_name);
CREATE INDEX idx_agent_recs_timestamp ON agent_recommendations(timestamp);

-- Ensemble Decisions: Synthesized recommendations from all agents
CREATE TABLE ensemble_decisions (
    ensemble_id VARCHAR(50) PRIMARY KEY DEFAULT ('ens_' || uuid_generate_v4()::text),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    voting_strategy VARCHAR(50) NOT NULL,
    agent_recommendations JSONB NOT NULL,
    final_recommendation JSONB NOT NULL,
    
    UNIQUE(case_id) -- One ensemble decision per case
);

CREATE INDEX idx_ensemble_case_id ON ensemble_decisions(case_id);
CREATE INDEX idx_ensemble_timestamp ON ensemble_decisions(timestamp);

-- ============================================================================
-- POLICY & CONFIGURATION TABLES
-- ============================================================================

-- Policies: Decision rules and workflow configuration
CREATE TABLE policies (
    policy_id VARCHAR(50) PRIMARY KEY DEFAULT ('pol_' || uuid_generate_v4()::text),
    policy_name VARCHAR(200) NOT NULL,
    version VARCHAR(20) NOT NULL,
    vertical VARCHAR(50) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50) NOT NULL,
    voting_strategy JSONB NOT NULL,
    rules JSONB NOT NULL,
    state_machine JSONB NOT NULL,
    
    UNIQUE(vertical, version),
    CONSTRAINT chk_only_one_active_per_vertical UNIQUE(vertical, active) 
        DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_policies_vertical ON policies(vertical);
CREATE INDEX idx_policies_active ON policies(active) WHERE active = true;

-- Policy Versions History (for audit trail)
CREATE TABLE policy_versions (
    version_id VARCHAR(50) PRIMARY KEY DEFAULT ('pv_' || uuid_generate_v4()::text),
    policy_id VARCHAR(50) NOT NULL REFERENCES policies(policy_id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    changes JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50) NOT NULL
);

CREATE INDEX idx_policy_versions_policy_id ON policy_versions(policy_id);

-- ============================================================================
-- AUDIT & LOGGING TABLES
-- ============================================================================

-- Audit Events: Immutable log of all state changes and decisions
CREATE TABLE audit_events (
    event_id VARCHAR(50) PRIMARY KEY DEFAULT ('evt_' || uuid_generate_v4()::text),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    actor JSONB NOT NULL,
    transition JSONB,
    reasoning JSONB,
    evidence_snapshot JSONB,
    agent_recommendation JSONB,
    policy_version VARCHAR(50),
    policy_rule_matched VARCHAR(200),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT chk_actor_structure CHECK (
        actor ? 'type' AND
        actor->>'type' IN ('system', 'human', 'api')
    )
);

CREATE INDEX idx_audit_case_id ON audit_events(case_id);
CREATE INDEX idx_audit_timestamp ON audit_events(timestamp);
CREATE INDEX idx_audit_event_type ON audit_events(event_type);
CREATE INDEX idx_audit_actor_type ON audit_events((actor->>'type'));

-- ============================================================================
-- QUEUE & ASSIGNMENT TABLES
-- ============================================================================

-- Queue Assignments: Cases assigned to human reviewers
CREATE TABLE queue_assignments (
    assignment_id VARCHAR(50) PRIMARY KEY DEFAULT ('asn_' || uuid_generate_v4()::text),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    queue VARCHAR(100) NOT NULL,
    assigned_role VARCHAR(50) NOT NULL,
    assigned_to_user VARCHAR(50),
    claimed_at TIMESTAMP,
    sla_deadline TIMESTAMP,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    CONSTRAINT chk_claimed_requires_user CHECK (
        (claimed_at IS NULL AND assigned_to_user IS NULL) OR
        (claimed_at IS NOT NULL AND assigned_to_user IS NOT NULL)
    )
);

CREATE INDEX idx_queue_assignments_queue ON queue_assignments(queue) 
    WHERE completed_at IS NULL;
CREATE INDEX idx_queue_assignments_user ON queue_assignments(assigned_to_user) 
    WHERE completed_at IS NULL;
CREATE INDEX idx_queue_assignments_sla ON queue_assignments(sla_deadline) 
    WHERE completed_at IS NULL AND sla_deadline IS NOT NULL;

-- ============================================================================
-- USER MANAGEMENT TABLES
-- ============================================================================

-- Users: System users (reviewers, compliance officers, etc.)
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY DEFAULT ('usr_' || uuid_generate_v4()::text),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(200),
    role VARCHAR(50) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(active) WHERE active = true;

-- User Sessions
CREATE TABLE user_sessions (
    session_id VARCHAR(50) PRIMARY KEY DEFAULT ('ses_' || uuid_generate_v4()::text),
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);

-- ============================================================================
-- ANALYTICS & METRICS TABLES
-- ============================================================================

-- Agent Performance Metrics
CREATE TABLE agent_metrics (
    metric_id VARCHAR(50) PRIMARY KEY DEFAULT ('met_' || uuid_generate_v4()::text),
    agent_name VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    total_recommendations INTEGER NOT NULL DEFAULT 0,
    agreements_with_humans INTEGER NOT NULL DEFAULT 0,
    avg_confidence DECIMAL(5,4),
    avg_processing_time_ms INTEGER,
    
    UNIQUE(agent_name, date)
);

CREATE INDEX idx_agent_metrics_date ON agent_metrics(date);
CREATE INDEX idx_agent_metrics_agent ON agent_metrics(agent_name);

-- Case Volume Metrics
CREATE TABLE case_metrics (
    metric_id VARCHAR(50) PRIMARY KEY DEFAULT ('met_' || uuid_generate_v4()::text),
    date DATE NOT NULL,
    vertical VARCHAR(50) NOT NULL,
    total_cases INTEGER NOT NULL DEFAULT 0,
    auto_approved INTEGER NOT NULL DEFAULT 0,
    auto_rejected INTEGER NOT NULL DEFAULT 0,
    manual_review INTEGER NOT NULL DEFAULT 0,
    avg_processing_time_seconds INTEGER,
    sla_breaches INTEGER NOT NULL DEFAULT 0,
    
    UNIQUE(date, vertical)
);

CREATE INDEX idx_case_metrics_date ON case_metrics(date);
CREATE INDEX idx_case_metrics_vertical ON case_metrics(vertical);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_cases_updated_at 
    BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active cases with ensemble recommendations
CREATE VIEW v_cases_with_recommendations AS
SELECT 
    c.case_id,
    c.vertical,
    c.status,
    c.priority,
    c.created_at,
    c.sla_deadline,
    c.policy_version,
    e.ensemble_id,
    e.final_recommendation,
    e.voting_strategy,
    qa.assignment_id,
    qa.queue,
    qa.assigned_to_user,
    qa.claimed_at
FROM cases c
LEFT JOIN ensemble_decisions e ON c.case_id = e.case_id
LEFT JOIN queue_assignments qa ON c.case_id = qa.case_id AND qa.completed_at IS NULL
WHERE c.status NOT IN ('approved', 'rejected', 'expired');

-- Queue dashboard view
CREATE VIEW v_queue_dashboard AS
SELECT 
    qa.queue,
    qa.assigned_role,
    COUNT(*) as total_cases,
    COUNT(qa.assigned_to_user) as claimed_cases,
    COUNT(*) - COUNT(qa.assigned_to_user) as unclaimed_cases,
    COUNT(CASE WHEN qa.sla_deadline < NOW() THEN 1 END) as sla_breached,
    AVG(EXTRACT(EPOCH FROM (NOW() - qa.created_at))) as avg_wait_time_seconds
FROM queue_assignments qa
WHERE qa.completed_at IS NULL
GROUP BY qa.queue, qa.assigned_role;

-- Agent accuracy view
CREATE VIEW v_agent_accuracy AS
SELECT 
    ar.agent_name,
    COUNT(*) as total_recommendations,
    SUM(CASE 
        WHEN ar.recommendation->>'action' = 
             (SELECT ae.transition->>'to_state' 
              FROM audit_events ae 
              WHERE ae.case_id = ar.case_id 
                AND ae.actor->>'type' = 'human'
                AND ae.transition->>'to_state' IN ('approved', 'rejected')
              ORDER BY ae.timestamp DESC LIMIT 1)
        THEN 1 ELSE 0 
    END) as agreements,
    ROUND(100.0 * SUM(CASE 
        WHEN ar.recommendation->>'action' = 
             (SELECT ae.transition->>'to_state' 
              FROM audit_events ae 
              WHERE ae.case_id = ar.case_id 
                AND ae.actor->>'type' = 'human'
                AND ae.transition->>'to_state' IN ('approved', 'rejected')
              ORDER BY ae.timestamp DESC LIMIT 1)
        THEN 1 ELSE 0 
    END) / COUNT(*), 2) as accuracy_pct,
    AVG((ar.recommendation->>'confidence')::float) as avg_confidence
FROM agent_recommendations ar
WHERE EXISTS (
    SELECT 1 FROM audit_events ae 
    WHERE ae.case_id = ar.case_id 
      AND ae.actor->>'type' = 'human'
      AND ae.transition->>'to_state' IN ('approved', 'rejected')
)
GROUP BY ar.agent_name;

-- ============================================================================
-- SAMPLE DATA (for development)
-- ============================================================================

-- Insert sample policy
INSERT INTO policies (
    policy_id, policy_name, version, vertical, active, created_by,
    voting_strategy, rules, state_machine
) VALUES (
    'pol_kyc_v1',
    'KYC Individual Verification',
    '1.0',
    'kyc',
    true,
    'system',
    '{
        "type": "risk_weighted",
        "config": {
            "high_risk_threshold": 70,
            "high_risk_consensus_required": "unanimous",
            "low_risk_threshold": 30,
            "low_risk_consensus_required": "majority",
            "agent_weights": {
                "compliance_agent": 2.0,
                "identity_agent": 1.0,
                "fraud_agent": 1.0,
                "risk_agent": 1.5
            }
        }
    }'::jsonb,
    '[
        {
            "priority": 1,
            "name": "Sanctions Hit",
            "condition": "compliance.sanctions_screening.status == \"hit\"",
            "action": "escalate",
            "assignee_role": "senior_compliance_officer",
            "sla_hours": 2
        },
        {
            "priority": 2,
            "name": "High Confidence Auto-Approve",
            "condition": "ensemble.confidence > 0.95 AND ensemble.risk_score < 20",
            "action": "auto_approve",
            "sla_hours": null
        },
        {
            "priority": 3,
            "name": "Low Confidence Manual Review",
            "condition": "ensemble.confidence < 0.70",
            "action": "manual_review",
            "assignee_role": "kyc_analyst",
            "sla_hours": 24
        },
        {
            "priority": 99,
            "name": "Default Manual Review",
            "condition": "*",
            "action": "manual_review",
            "assignee_role": "kyc_analyst",
            "sla_hours": 24
        }
    ]'::jsonb,
    '{
        "states": [
            "draft", "submitted", "processing",
            "under_review", "under_review.identity_check", "under_review.fraud_check",
            "under_review.compliance_check", "under_review.manual_review",
            "approved", "rejected", "needs_more_info", "expired"
        ],
        "transitions": {
            "draft → submitted": {"allowed_actors": ["customer", "api"]},
            "submitted → processing": {"allowed_actors": ["system"]},
            "processing → under_review.*": {"allowed_actors": ["system", "workflow_engine"]},
            "under_review.* → approved": {"allowed_actors": ["workflow_engine", "reviewer"]},
            "under_review.* → rejected": {"allowed_actors": ["workflow_engine", "reviewer"]},
            "under_review.* → needs_more_info": {"allowed_actors": ["reviewer"]},
            "needs_more_info → submitted": {"allowed_actors": ["customer"]},
            "* → expired": {"allowed_actors": ["system"]}
        },
        "terminal_states": ["approved", "rejected", "expired"]
    }'::jsonb
);

-- Insert sample users
INSERT INTO users (user_id, email, full_name, role) VALUES
    ('usr_admin', 'admin@example.com', 'Admin User', 'admin'),
    ('usr_analyst1', 'analyst1@example.com', 'Jane Analyst', 'kyc_analyst'),
    ('usr_compliance1', 'compliance1@example.com', 'John Compliance', 'senior_compliance_officer');

-- ============================================================================
-- GRANTS (adjust based on your security requirements)
-- ============================================================================

-- Create application user (run this separately with proper credentials)
-- CREATE USER decision_platform_app WITH PASSWORD 'your_secure_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO decision_platform_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO decision_platform_app;

-- Create read-only user for analytics
-- CREATE USER decision_platform_readonly WITH PASSWORD 'your_secure_password';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO decision_platform_readonly;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO decision_platform_readonly;
