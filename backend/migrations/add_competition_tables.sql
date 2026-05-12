-- Migration: Add competition system tables
-- Tables: campaign_participants, wallet_deposits, reward_distributions

-- Campaign Participants (per-campaign scores and ranks)
CREATE TABLE IF NOT EXISTS campaign_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    user_id UUID NOT NULL REFERENCES users(id),
    contribution_score FLOAT DEFAULT 0.0,
    validated_units INTEGER DEFAULT 0,
    rank INTEGER DEFAULT 0,
    reward_earned_sol FLOAT DEFAULT 0.0,
    reward_tx_signature VARCHAR(255),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    last_score_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cp_campaign ON campaign_participants(campaign_id);
CREATE INDEX IF NOT EXISTS idx_cp_user ON campaign_participants(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cp_campaign_user ON campaign_participants(campaign_id, user_id);

-- Wallet Deposits (on-chain SOL deposit records)
CREATE TABLE IF NOT EXISTS wallet_deposits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    wallet_address VARCHAR(255) NOT NULL,
    tx_signature VARCHAR(255) UNIQUE NOT NULL,
    amount_sol FLOAT NOT NULL,
    amount_lamports FLOAT,
    status VARCHAR(20) DEFAULT 'confirmed',
    category VARCHAR(50) DEFAULT 'deposit',
    campaign_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wd_user ON wallet_deposits(user_id);
CREATE INDEX IF NOT EXISTS idx_wd_sig ON wallet_deposits(tx_signature);

-- Reward Distributions (treasury payouts to contributors)
CREATE TABLE IF NOT EXISTS reward_distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    user_id UUID NOT NULL REFERENCES users(id),
    wallet_address VARCHAR(255) NOT NULL,
    amount_sol FLOAT NOT NULL,
    tx_signature VARCHAR(255),
    rank INTEGER DEFAULT 0,
    tier VARCHAR(20) DEFAULT 'participation',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rd_campaign ON reward_distributions(campaign_id);
CREATE INDEX IF NOT EXISTS idx_rd_user ON reward_distributions(user_id);
