-- Ensure latency/cost columns exist on appels
ALTER TABLE public.appels ADD COLUMN IF NOT EXISTS latency_metrics JSONB;
ALTER TABLE public.appels ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC;
ALTER TABLE public.appels ADD COLUMN IF NOT EXISTS cost_breakdown JSONB;

DROP VIEW IF EXISTS public.vw_appels_clients;

CREATE VIEW public.vw_appels_clients AS
SELECT
  a.id,
  a.client_id,
  a.room_name,
  a.caller_number,
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

CREATE VIEW public.vw_stats_appels_clients AS
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

GRANT SELECT ON public.vw_appels_clients TO anon, authenticated, service_role;
GRANT SELECT ON public.vw_stats_appels_clients TO anon, authenticated, service_role;