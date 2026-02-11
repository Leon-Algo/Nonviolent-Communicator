BEGIN;

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  session_id UUID REFERENCES sessions(id),
  endpoint VARCHAR(80) NOT NULL,
  client_message_id UUID NOT NULL,
  response_body JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_idempotency_message UNIQUE (user_id, session_id, endpoint, client_message_id)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_created_at ON idempotency_keys (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_idempotency_session ON idempotency_keys (session_id, created_at DESC);

COMMIT;
