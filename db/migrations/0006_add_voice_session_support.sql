BEGIN;

ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS modality TEXT NOT NULL DEFAULT 'TEXT',
  ADD COLUMN IF NOT EXISTS voice_channel_name TEXT,
  ADD COLUMN IF NOT EXISTS voice_agent_id TEXT,
  ADD COLUMN IF NOT EXISTS voice_user_uid TEXT,
  ADD COLUMN IF NOT EXISTS voice_agent_uid TEXT,
  ADD COLUMN IF NOT EXISTS voice_status TEXT,
  ADD COLUMN IF NOT EXISTS voice_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS voice_ended_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS voice_expires_at TIMESTAMPTZ;

ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'TEXT_INPUT',
  ADD COLUMN IF NOT EXISTS external_turn_id TEXT,
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE sessions
  DROP CONSTRAINT IF EXISTS sessions_modality_check,
  ADD CONSTRAINT sessions_modality_check
  CHECK (modality IN ('TEXT', 'VOICE'));

ALTER TABLE sessions
  DROP CONSTRAINT IF EXISTS sessions_voice_status_check,
  ADD CONSTRAINT sessions_voice_status_check
  CHECK (
    voice_status IS NULL
    OR voice_status IN ('STARTING', 'STARTED', 'STOPPING', 'STOPPED', 'FAILED', 'EXPIRED')
  );

ALTER TABLE messages
  DROP CONSTRAINT IF EXISTS messages_source_check,
  ADD CONSTRAINT messages_source_check
  CHECK (source IN ('TEXT_INPUT', 'VOICE_TRANSCRIPT'));

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_external_turn_role
ON messages (session_id, external_turn_id, role)
WHERE external_turn_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_sessions_voice_agent_id
ON sessions (voice_agent_id)
WHERE voice_agent_id IS NOT NULL;

COMMIT;
