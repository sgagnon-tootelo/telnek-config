-- Fix fetch_profiles_for_admin Forbidden (42501) when dashboard uses service_role
-- or when profiles.id does not match auth.uid() but email matches.

CREATE OR REPLACE FUNCTION public.is_dashboard_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    COALESCE(auth.jwt() ->> 'role', '') = 'service_role'
    OR EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE role = 'admin'
        AND (
          id = auth.uid()
          OR lower(email) = lower(COALESCE(auth.jwt() ->> 'email', ''))
        )
    );
$$;

REVOKE ALL ON FUNCTION public.is_dashboard_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_dashboard_admin() TO authenticated, service_role;

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
  IF NOT public.is_dashboard_admin() THEN
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