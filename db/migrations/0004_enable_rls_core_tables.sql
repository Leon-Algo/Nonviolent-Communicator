BEGIN;

-- Supabase uses this role for authenticated user traffic.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN;
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public.request_user_id()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  raw_sub TEXT;
BEGIN
  raw_sub := current_setting('request.jwt.claim.sub', true);
  IF raw_sub IS NULL OR btrim(raw_sub) = '' THEN
    RETURN NULL;
  END IF;

  BEGIN
    RETURN raw_sub::UUID;
  EXCEPTION
    WHEN invalid_text_representation THEN
      RETURN NULL;
  END;
END;
$$;

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  users,
  scenes,
  sessions,
  messages,
  feedback_items,
  rewrites,
  summaries,
  reflections,
  event_logs,
  idempotency_keys
TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO authenticated;

ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS scenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS scenes FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS messages FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS feedback_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS feedback_items FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS rewrites ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS rewrites FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS summaries FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS reflections ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS reflections FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS event_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS event_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS idempotency_keys FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_owner_all ON users;
CREATE POLICY users_owner_all ON users
FOR ALL TO authenticated
USING (id = public.request_user_id())
WITH CHECK (id = public.request_user_id());

DROP POLICY IF EXISTS scenes_owner_all ON scenes;
CREATE POLICY scenes_owner_all ON scenes
FOR ALL TO authenticated
USING (user_id = public.request_user_id())
WITH CHECK (user_id = public.request_user_id());

DROP POLICY IF EXISTS sessions_owner_all ON sessions;
CREATE POLICY sessions_owner_all ON sessions
FOR ALL TO authenticated
USING (user_id = public.request_user_id())
WITH CHECK (user_id = public.request_user_id());

DROP POLICY IF EXISTS reflections_owner_all ON reflections;
CREATE POLICY reflections_owner_all ON reflections
FOR ALL TO authenticated
USING (user_id = public.request_user_id())
WITH CHECK (user_id = public.request_user_id());

DROP POLICY IF EXISTS event_logs_owner_all ON event_logs;
CREATE POLICY event_logs_owner_all ON event_logs
FOR ALL TO authenticated
USING (user_id = public.request_user_id())
WITH CHECK (user_id = public.request_user_id());

DROP POLICY IF EXISTS idempotency_owner_all ON idempotency_keys;
CREATE POLICY idempotency_owner_all ON idempotency_keys
FOR ALL TO authenticated
USING (user_id = public.request_user_id())
WITH CHECK (user_id = public.request_user_id());

DROP POLICY IF EXISTS messages_session_owner_all ON messages;
CREATE POLICY messages_session_owner_all ON messages
FOR ALL TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = messages.session_id
      AND s.user_id = public.request_user_id()
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = messages.session_id
      AND s.user_id = public.request_user_id()
  )
);

DROP POLICY IF EXISTS feedback_session_owner_all ON feedback_items;
CREATE POLICY feedback_session_owner_all ON feedback_items
FOR ALL TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = feedback_items.session_id
      AND s.user_id = public.request_user_id()
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = feedback_items.session_id
      AND s.user_id = public.request_user_id()
  )
);

DROP POLICY IF EXISTS rewrites_session_owner_all ON rewrites;
CREATE POLICY rewrites_session_owner_all ON rewrites
FOR ALL TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = rewrites.session_id
      AND s.user_id = public.request_user_id()
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = rewrites.session_id
      AND s.user_id = public.request_user_id()
  )
);

DROP POLICY IF EXISTS summaries_session_owner_all ON summaries;
CREATE POLICY summaries_session_owner_all ON summaries
FOR ALL TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = summaries.session_id
      AND s.user_id = public.request_user_id()
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM sessions s
    WHERE s.id = summaries.session_id
      AND s.user_id = public.request_user_id()
  )
);

COMMIT;
