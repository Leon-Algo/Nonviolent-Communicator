BEGIN;

CREATE OR REPLACE FUNCTION public.request_user_id()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  raw_sub TEXT;
  raw_claims TEXT;
  resolved_uid UUID;
BEGIN
  -- Preferred path in Supabase runtime.
  IF to_regprocedure('auth.uid()') IS NOT NULL THEN
    BEGIN
      resolved_uid := auth.uid();
      IF resolved_uid IS NOT NULL THEN
        RETURN resolved_uid;
      END IF;
    EXCEPTION
      WHEN undefined_function THEN
        NULL;
    END;
  END IF;

  -- Fallback for app-managed DB sessions.
  raw_sub := current_setting('request.jwt.claim.sub', true);

  -- Fallback for runtimes that expose JSON claims blob only.
  IF raw_sub IS NULL OR btrim(raw_sub) = '' THEN
    raw_claims := current_setting('request.jwt.claims', true);
    IF raw_claims IS NOT NULL AND btrim(raw_claims) <> '' THEN
      BEGIN
        raw_sub := (raw_claims::jsonb ->> 'sub');
      EXCEPTION
        WHEN others THEN
          raw_sub := NULL;
      END;
    END IF;
  END IF;

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

COMMIT;
