-- Expose auth.users.last_sign_in_at to admin dashboard (read-only via RPC).

CREATE OR REPLACE FUNCTION public.fetch_profiles_for_admin()
RETURNS TABLE (
  id uuid,
  email text,
  role text,
  client_id text,
  created_at timestamptz,
  last_sign_in_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'forbidden' USING ERRCODE = '42501';
  END IF;

  RETURN QUERY
  SELECT
    p.id,
    p.email,
    p.role,
    p.client_id,
    p.created_at,
    u.last_sign_in_at
  FROM public.profiles p
  LEFT JOIN auth.users u ON u.id = p.id
  ORDER BY p.email;
END;
$$;

REVOKE ALL ON FUNCTION public.fetch_profiles_for_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.fetch_profiles_for_admin() TO authenticated, service_role;