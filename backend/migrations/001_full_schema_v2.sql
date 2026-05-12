-- ═══════════════════════════════════════════════════════════════════
-- DeSci Compute Platform — Supabase Migration V2
-- Fully Supabase-compatible (no IF NOT EXISTS on policies/columns)
-- Run in Supabase Dashboard → SQL Editor → New Query → Run
-- ═══════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────
-- STEP 1: Create new ENUM types
-- (wrapped in DO blocks for idempotency)
-- ──────────────────────────────────────────────

DO $$ BEGIN
  CREATE TYPE datasetformat AS ENUM ('csv', 'json', 'parquet');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE uploadstatus AS ENUM ('pending', 'uploading', 'chunking', 'ready', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE aggregationstatus AS ENUM ('in_progress', 'completed', 'failed', 'stale');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE actionstatus AS ENUM ('pending', 'executed', 'failed', 'skipped');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE campaignstatus AS ENUM ('active', 'completed', 'cancelled', 'expired');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;


-- ──────────────────────────────────────────────
-- STEP 2: ALTER existing tables — add new columns
-- (wrapped in DO blocks so re-running won't error)
-- ──────────────────────────────────────────────

-- task_results: add execution_time_ms
DO $$ BEGIN
  ALTER TABLE task_results ADD COLUMN execution_time_ms INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- task_results: add consensus_group
DO $$ BEGIN
  ALTER TABLE task_results ADD COLUMN consensus_group VARCHAR(64);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- task_results: add checksum
DO $$ BEGIN
  ALTER TABLE task_results ADD COLUMN checksum VARCHAR(64);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- task_results: add is_canonical
DO $$ BEGIN
  ALTER TABLE task_results ADD COLUMN is_canonical BOOLEAN DEFAULT false;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- events: add job_id
DO $$ BEGIN
  ALTER TABLE events ADD COLUMN job_id UUID REFERENCES jobs(id);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- events: add device_id
DO $$ BEGIN
  ALTER TABLE events ADD COLUMN device_id UUID REFERENCES devices(id);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- events: add index on event_name
DO $$ BEGIN
  CREATE INDEX idx_events_event_name ON events(event_name);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;


-- ──────────────────────────────────────────────
-- STEP 3: NEW TABLE — datasets
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS datasets (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename             VARCHAR(512) NOT NULL,
  storage_path         VARCHAR(1024) NOT NULL,
  format               datasetformat NOT NULL,
  row_count            INTEGER DEFAULT 0,
  column_metadata_json TEXT DEFAULT '{}',
  upload_status        uploadstatus DEFAULT 'pending',
  size_bytes           INTEGER DEFAULT 0,
  created_at           TIMESTAMPTZ DEFAULT now()
);


-- ──────────────────────────────────────────────
-- STEP 4: NEW TABLE — dataset_chunks
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dataset_chunks (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id   UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  chunk_index  INTEGER NOT NULL,
  storage_path VARCHAR(1024) NOT NULL,
  row_start    INTEGER NOT NULL,
  row_end      INTEGER NOT NULL,
  checksum     VARCHAR(64) NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT now()
);


-- ──────────────────────────────────────────────
-- STEP 5: NEW TABLE — aggregated_results
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS aggregated_results (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id               UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  aggregation_version  INTEGER DEFAULT 1,
  metrics_json         TEXT NOT NULL DEFAULT '{}',
  completed_tasks      INTEGER DEFAULT 0,
  total_tasks          INTEGER DEFAULT 0,
  aggregation_status   aggregationstatus DEFAULT 'in_progress',
  checkpoint_json      TEXT DEFAULT '{}',
  updated_at           TIMESTAMPTZ DEFAULT now()
);

DO $$ BEGIN
  CREATE INDEX idx_aggregated_results_job_id ON aggregated_results(job_id);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;


-- ──────────────────────────────────────────────
-- STEP 6: NEW TABLE — researcher_outputs
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS researcher_outputs (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id             UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  report_path        VARCHAR(1024),
  visualization_path VARCHAR(1024),
  export_path        VARCHAR(1024),
  summary_json       TEXT DEFAULT '{}',
  generated_at       TIMESTAMPTZ DEFAULT now()
);

DO $$ BEGIN
  CREATE INDEX idx_researcher_outputs_job_id ON researcher_outputs(job_id);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;


-- ──────────────────────────────────────────────
-- STEP 7: NEW TABLE — mcp_actions
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS mcp_actions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_type     VARCHAR(100) NOT NULL,
  target_job_id   UUID REFERENCES jobs(id),
  target_user_id  UUID REFERENCES users(id),
  parameters_json TEXT DEFAULT '{}',
  status          actionstatus DEFAULT 'pending',
  source          VARCHAR(20) DEFAULT 'rule_engine',
  created_at      TIMESTAMPTZ DEFAULT now()
);

DO $$ BEGIN
  CREATE INDEX idx_mcp_actions_type ON mcp_actions(action_type);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;


-- ──────────────────────────────────────────────
-- STEP 8: NEW TABLE — reward_campaigns
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS reward_campaigns (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_type  VARCHAR(100) NOT NULL,
  multiplier     DOUBLE PRECISION DEFAULT 1.0,
  target_job_id  UUID REFERENCES jobs(id),
  start_time     TIMESTAMPTZ DEFAULT now(),
  end_time       TIMESTAMPTZ,
  status         campaignstatus DEFAULT 'active',
  metadata_json  TEXT DEFAULT '{}'
);


-- ──────────────────────────────────────────────
-- STEP 9: NEW TABLE — user_retention_state
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_retention_state (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  streak_days           INTEGER DEFAULT 0,
  longest_streak        INTEGER DEFAULT 0,
  inactivity_score      DOUBLE PRECISION DEFAULT 0.0,
  churn_risk_score      DOUBLE PRECISION DEFAULT 0.0,
  total_validated_tasks INTEGER DEFAULT 0,
  reliability_score     DOUBLE PRECISION DEFAULT 1.0,
  last_reward_at        TIMESTAMPTZ,
  last_compute_at       TIMESTAMPTZ,
  updated_at            TIMESTAMPTZ DEFAULT now()
);


-- ──────────────────────────────────────────────
-- STEP 10: Enable RLS on all new tables
-- ──────────────────────────────────────────────

ALTER TABLE datasets              ENABLE ROW LEVEL SECURITY;
ALTER TABLE dataset_chunks        ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_results    ENABLE ROW LEVEL SECURITY;
ALTER TABLE researcher_outputs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_actions           ENABLE ROW LEVEL SECURITY;
ALTER TABLE reward_campaigns      ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_retention_state  ENABLE ROW LEVEL SECURITY;


-- ──────────────────────────────────────────────
-- STEP 11: RLS Policies — full access for service_role
-- (DROP + CREATE pattern for idempotency since
--  CREATE POLICY IF NOT EXISTS doesn't exist in PG)
-- ──────────────────────────────────────────────

DROP POLICY IF EXISTS "service_all" ON datasets;
CREATE POLICY "service_all" ON datasets FOR ALL
  TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_all" ON dataset_chunks;
CREATE POLICY "service_all" ON dataset_chunks FOR ALL
  TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_all" ON aggregated_results;
CREATE POLICY "service_all" ON aggregated_results FOR ALL
  TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_all" ON researcher_outputs;
CREATE POLICY "service_all" ON researcher_outputs FOR ALL
  TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_all" ON mcp_actions;
CREATE POLICY "service_all" ON mcp_actions FOR ALL
  TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_all" ON reward_campaigns;
CREATE POLICY "service_all" ON reward_campaigns FOR ALL
  TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_all" ON user_retention_state;
CREATE POLICY "service_all" ON user_retention_state FOR ALL
  TO service_role USING (true) WITH CHECK (true);


-- ──────────────────────────────────────────────
-- STEP 12: Grant permissions
-- ──────────────────────────────────────────────

GRANT ALL ON datasets             TO service_role;
GRANT ALL ON dataset_chunks       TO service_role;
GRANT ALL ON aggregated_results   TO service_role;
GRANT ALL ON researcher_outputs   TO service_role;
GRANT ALL ON mcp_actions          TO service_role;
GRANT ALL ON reward_campaigns     TO service_role;
GRANT ALL ON user_retention_state TO service_role;


-- ══════════════════════════════════════════════
-- ✅ DONE — Safe to re-run at any time
--
-- New tables: datasets, dataset_chunks,
--   aggregated_results, researcher_outputs,
--   mcp_actions, reward_campaigns,
--   user_retention_state
--
-- Altered: task_results (+4 cols), events (+2 cols)
-- ══════════════════════════════════════════════
