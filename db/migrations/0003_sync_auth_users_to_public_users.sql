BEGIN;

CREATE OR REPLACE FUNCTION public.sync_public_user_from_auth()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_email TEXT;
  v_display_name TEXT;
BEGIN
  v_email := lower(trim(coalesce(NEW.email, '')));
  IF v_email = '' THEN
    RETURN NEW;
  END IF;

  v_display_name := left(
    coalesce(
      NEW.raw_user_meta_data ->> 'full_name',
      split_part(v_email, '@', 1),
      'User'
    ),
    120
  );

  INSERT INTO public.users (id, email, display_name)
  VALUES (NEW.id, v_email, v_display_name)
  ON CONFLICT (id) DO UPDATE
  SET email = EXCLUDED.email,
      display_name = EXCLUDED.display_name,
      updated_at = NOW();

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_saved ON auth.users;
CREATE TRIGGER on_auth_user_saved
AFTER INSERT OR UPDATE OF email, raw_user_meta_data
ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.sync_public_user_from_auth();

INSERT INTO public.users (id, email, display_name)
SELECT
  au.id,
  lower(trim(au.email)) AS email,
  left(
    coalesce(
      au.raw_user_meta_data ->> 'full_name',
      split_part(lower(trim(au.email)), '@', 1),
      'User'
    ),
    120
  ) AS display_name
FROM auth.users AS au
WHERE au.email IS NOT NULL
  AND trim(au.email) <> ''
ON CONFLICT (id) DO UPDATE
SET email = EXCLUDED.email,
    display_name = EXCLUDED.display_name,
    updated_at = NOW();

COMMIT;
