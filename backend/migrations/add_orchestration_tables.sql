-- Migration: Add autonomous incentive orchestration tables
-- Tables: treasury_ledger, treasury_transactions, incentive_campaigns

-- Treasury Ledger (single-row state)
CREATE TABLE IF NOT EXISTS treasury_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    total_balance FLOAT NOT NULL DEFAULT 100000.0,
    reserved_emergency FLOAT NOT NULL DEFAULT 10000.0,
    allocated_retention FLOAT DEFAULT 0.0,
    allocated_supply FLOAT DEFAULT 0.0,  
    allocated_referral FLOAT DEFAULT 0.0,
    allocated_streak FLOAT DEFAULT 0.0,
    allocated_experimental FLOAT DEFAULT 0.0,
    total_spent FLOAT DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed treasury with initial balance
INSERT INTO treasury_ledger (total_balance, reserved_emergency) 
VALUES (100000.0, 10000.0)
ON CONFLICT DO NOTHING;

-- Treasury Transactions
CREATE TABLE IF NOT EXISTS treasury_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID,
    category VARCHAR(50) NOT NULL,
    amount FLOAT NOT NULL,
    description VARCHAR(512),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Incentive Campaigns
CREATE TABLE IF NOT EXISTS incentive_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    campaign_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'proposed',
    reasoning TEXT,
    target_audience VARCHAR(255),
    reward_pool FLOAT DEFAULT 0.0,
    spent FLOAT DEFAULT 0.0,
    max_per_user FLOAT DEFAULT 100.0,
    duration_hours INTEGER DEFAULT 24,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    torque_primitives_json TEXT DEFAULT '[]',
    torque_campaign_id VARCHAR(255),
    eligibility_rules_json TEXT DEFAULT '[]',
    success_metrics_json TEXT DEFAULT '[]',
    performance_json TEXT DEFAULT '{}',
    target_job_id UUID REFERENCES jobs(id),
    target_dataset_id UUID REFERENCES datasets(id),
    multiplier FLOAT DEFAULT 1.0,
    source VARCHAR(30) DEFAULT 'rule_engine',
    created_by_cycle INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_incentive_campaigns_type ON incentive_campaigns(campaign_type);
CREATE INDEX IF NOT EXISTS idx_incentive_campaigns_status ON incentive_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_treasury_transactions_category ON treasury_transactions(category);
CREATE INDEX IF NOT EXISTS idx_treasury_transactions_campaign ON treasury_transactions(campaign_id);
