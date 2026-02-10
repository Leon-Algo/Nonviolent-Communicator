BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  locale TEXT NOT NULL DEFAULT 'zh-CN',
  timezone TEXT NOT NULL DEFAULT 'UTC',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scenes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  title VARCHAR(80) NOT NULL,
  template_id VARCHAR(32) NOT NULL CHECK (template_id IN ('PEER_FEEDBACK', 'MANAGER_ALIGNMENT', 'CROSS_TEAM_CONFLICT', 'CUSTOM')),
  counterparty_role VARCHAR(16) NOT NULL CHECK (counterparty_role IN ('PEER', 'MANAGER', 'REPORT', 'CLIENT', 'OTHER')),
  relationship_level VARCHAR(16) NOT NULL CHECK (relationship_level IN ('SMOOTH', 'NEUTRAL', 'TENSE')),
  goal VARCHAR(240) NOT NULL,
  pain_points JSONB NOT NULL DEFAULT '[]'::jsonb,
  context TEXT NOT NULL,
  power_dynamic VARCHAR(24) NOT NULL CHECK (power_dynamic IN ('USER_HIGHER', 'PEER_LEVEL', 'COUNTERPART_HIGHER')),
  status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  scene_id UUID NOT NULL REFERENCES scenes(id),
  state VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' CHECK (state IN ('ACTIVE', 'COMPLETED', 'ABANDONED')),
  target_turns SMALLINT NOT NULL CHECK (target_turns BETWEEN 5 AND 8),
  current_turn SMALLINT NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id),
  role VARCHAR(16) NOT NULL CHECK (role IN ('USER', 'ASSISTANT', 'SYSTEM')),
  turn_no SMALLINT NOT NULL CHECK (turn_no >= 0),
  content TEXT NOT NULL,
  latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
  token_in INTEGER CHECK (token_in IS NULL OR token_in >= 0),
  token_out INTEGER CHECK (token_out IS NULL OR token_out >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id),
  user_message_id UUID UNIQUE NOT NULL REFERENCES messages(id),
  overall_score SMALLINT NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
  risk_level VARCHAR(16) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
  ofnr_detail JSONB NOT NULL,
  next_best_sentence TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rewrites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id),
  source_message_id UUID NOT NULL REFERENCES messages(id),
  rewrite_style VARCHAR(16) NOT NULL CHECK (rewrite_style IN ('NEUTRAL')),
  rewritten_content TEXT NOT NULL,
  accepted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID UNIQUE NOT NULL REFERENCES sessions(id),
  opening_line TEXT NOT NULL,
  request_line TEXT NOT NULL,
  fallback_line TEXT,
  risk_triggers JSONB NOT NULL DEFAULT '[]'::jsonb,
  edited_by_user BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reflections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  session_id UUID UNIQUE NOT NULL REFERENCES sessions(id),
  used_in_real_world BOOLEAN NOT NULL,
  outcome_score SMALLINT CHECK (outcome_score BETWEEN 1 AND 5),
  blocker_code VARCHAR(24) CHECK (blocker_code IS NULL OR blocker_code IN ('NO_CHANCE', 'EMOTION_SPIKE', 'POWER_GAP', 'WORDING_ISSUE', 'OTHER')),
  blocker_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT reflections_score_nullable CHECK (outcome_score IS NULL OR outcome_score BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS event_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  session_id UUID REFERENCES sessions(id),
  event_name VARCHAR(64) NOT NULL,
  event_props JSONB NOT NULL DEFAULT '{}'::jsonb,
  client_ts TIMESTAMPTZ,
  server_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenes_user_updated ON scenes (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_scene_state ON sessions (scene_id, state);
CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON sessions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_turn ON messages (session_id, turn_no, created_at);
CREATE INDEX IF NOT EXISTS idx_rewrites_source ON rewrites (source_message_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_logs_event_time ON event_logs (event_name, server_ts DESC);
CREATE INDEX IF NOT EXISTS idx_event_logs_user_time ON event_logs (user_id, server_ts DESC);

DROP TRIGGER IF EXISTS trg_users_set_updated_at ON users;
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_scenes_set_updated_at ON scenes;
CREATE TRIGGER trg_scenes_set_updated_at
BEFORE UPDATE ON scenes
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_summaries_set_updated_at ON summaries;
CREATE TRIGGER trg_summaries_set_updated_at
BEFORE UPDATE ON summaries
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

COMMIT;
