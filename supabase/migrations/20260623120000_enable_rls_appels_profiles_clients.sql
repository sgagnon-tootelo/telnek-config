-- Row Level Security for Telnek dashboard + LiveKit agent architecture.
--
-- Prerequisites (Streamlit / telnek-config secrets):
--   SUPABASE_KEY must be the anon (publishable) key, NOT service_role.
--   After sign_in_with_password the SDK sends the user JWT and policies apply.
--
-- Backend writers (no policy needed — service_role bypasses RLS):
--   GrokVoiceAgent (SUPABASE_KEY = service_role)
--   Edge function twilio-sms-reply (SUPABASE_SERVICE_ROLE_KEY)

-- ---------------------------------------------------------------------------
-- Helper functions (SECURITY DEFINER to read profiles without circular RLS)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.profiles
    WHERE id = auth.uid()
      AND role = 'admin'
  );
$$;

CREATE OR REPLACE FUNCTION public.current_user_client_id()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT client_id
  FROM public.profiles
  WHERE id = auth.uid()
  LIMIT 1;
$$;

REVOKE ALL ON FUNCTION public.is_admin() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.current_user_client_id() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.current_user_client_id() TO authenticated, service_role;

-- ---------------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------------

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profiles_select_own ON public.profiles;
CREATE POLICY profiles_select_own
  ON public.profiles
  FOR SELECT
  TO authenticated
  USING (id = auth.uid());

-- ---------------------------------------------------------------------------
-- clients
-- ---------------------------------------------------------------------------

ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS clients_select_admin ON public.clients;
CREATE POLICY clients_select_admin
  ON public.clients
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

DROP POLICY IF EXISTS clients_select_client ON public.clients;
CREATE POLICY clients_select_client
  ON public.clients
  FOR SELECT
  TO authenticated
  USING (id = public.current_user_client_id());

DROP POLICY IF EXISTS clients_update_admin ON public.clients;
CREATE POLICY clients_update_admin
  ON public.clients
  FOR UPDATE
  TO authenticated
  USING (public.is_admin())
  WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS clients_update_client ON public.clients;
CREATE POLICY clients_update_client
  ON public.clients
  FOR UPDATE
  TO authenticated
  USING (id = public.current_user_client_id())
  WITH CHECK (id = public.current_user_client_id());

-- ---------------------------------------------------------------------------
-- appels (read-only for dashboard users; writes via service_role agent)
-- ---------------------------------------------------------------------------

ALTER TABLE public.appels ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS appels_select_admin ON public.appels;
CREATE POLICY appels_select_admin
  ON public.appels
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

DROP POLICY IF EXISTS appels_select_client ON public.appels;
CREATE POLICY appels_select_client
  ON public.appels
  FOR SELECT
  TO authenticated
  USING (client_id = public.current_user_client_id());

-- ---------------------------------------------------------------------------
-- voices (reference data for config UI)
-- ---------------------------------------------------------------------------

ALTER TABLE public.voices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS voices_select_authenticated ON public.voices;
CREATE POLICY voices_select_authenticated
  ON public.voices
  FOR SELECT
  TO authenticated
  USING (true);

-- ---------------------------------------------------------------------------
-- known_callers (optional dashboard read; agent writes via service_role)
-- ---------------------------------------------------------------------------

ALTER TABLE public.known_callers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS known_callers_select_admin ON public.known_callers;
CREATE POLICY known_callers_select_admin
  ON public.known_callers
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

DROP POLICY IF EXISTS known_callers_select_client ON public.known_callers;
CREATE POLICY known_callers_select_client
  ON public.known_callers
  FOR SELECT
  TO authenticated
  USING (client_id = public.current_user_client_id());

-- ---------------------------------------------------------------------------
-- Views: security_invoker so RLS on underlying tables is enforced
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS public.vw_appels_clients;

CREATE VIEW public.vw_appels_clients
WITH (security_invoker = true)
AS
SELECT
  a.id,
  a.client_id,
  a.room_name,
  a.caller_number,
  a.caller_name,
  a.formatted_caller,
  a.started_at,
  a.ended_at,
  a.duration_seconds,
  a.transfer_mode,
  a.transfer_attempted,
  a.transfer_success,
  a.transfer_to_number,
  a.transfer_department,
  a.message_taken,
  a.message_name,
  a.message_number,
  a.message_reason,
  a.status,
  a.created_at,
  a.updated_at,
  a.transfer_client_name,
  a.appointment_booked,
  a.appointment_start,
  a.appointment_name,
  a.appointment_number,
  a.appointment_reason,
  a.twilio_call_sid,
  a.recording_url,
  a.transcript,
  a.transcript_json,
  a.recording_sid,
  a.reminder_sent,
  a.google_event_id,
  a.appointment_confirmed,
  a.appointment_cancelled,
  a.latency_metrics,
  a.estimated_cost_usd,
  a.cost_breakdown,
  c.company_name,
  to_char(a.started_at AT TIME ZONE 'America/Montreal', 'YYYY-MM-DD') AS call_date,
  to_char(a.started_at AT TIME ZONE 'America/Montreal', 'HH24:MI') AS call_time,
  CASE a.status
    WHEN 'completed' THEN 'Terminé'
    WHEN 'abandoned' THEN 'Abandonné'
    WHEN 'transferred' THEN 'Transféré'
    WHEN 'voicemail' THEN 'Message vocal'
    ELSE a.status
  END AS status_label,
  CASE
    WHEN a.appointment_booked THEN 'RDV réservé'
    ELSE ''
  END AS appointment_status_badge,
  CASE
    WHEN NOT COALESCE(a.appointment_booked, false) THEN ''
    WHEN COALESCE(a.appointment_cancelled, false) THEN '❌ Annulé'
    WHEN COALESCE(a.appointment_confirmed, false) THEN '✅ Confirmé'
    ELSE '⏳ À confirmer'
  END AS statut_rdv
FROM public.appels a
LEFT JOIN public.clients c ON c.id = a.client_id;

DROP VIEW IF EXISTS public.vw_stats_appels_clients;

CREATE VIEW public.vw_stats_appels_clients
WITH (security_invoker = true)
AS
SELECT
  a.client_id,
  COUNT(*)::int AS total_appels,
  COUNT(*) FILTER (WHERE a.status = 'completed')::int AS appels_completes,
  COUNT(*) FILTER (WHERE COALESCE(a.appointment_booked, false))::int AS rdv_reserves,
  COUNT(*) FILTER (WHERE COALESCE(a.appointment_confirmed, false))::int AS rdv_confirmes,
  COUNT(*) FILTER (WHERE COALESCE(a.appointment_cancelled, false))::int AS rdv_annules,
  ROUND(AVG(a.duration_seconds)::numeric, 1) AS duree_moyenne_sec,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE COALESCE(a.appointment_booked, false))
    / NULLIF(COUNT(*), 0),
    1
  ) AS pourcentage_rdv
FROM public.appels a
GROUP BY a.client_id;

GRANT SELECT ON public.vw_appels_clients TO authenticated, service_role;
GRANT SELECT ON public.vw_stats_appels_clients TO authenticated, service_role;