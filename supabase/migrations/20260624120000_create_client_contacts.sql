-- Unified client contact directory (phase 1: table + RLS + migrate transfer_numbers JSON).
-- Agent reads client_contacts with dual compat fallback to clients.transfer_numbers.

-- ---------------------------------------------------------------------------
-- Table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.client_contacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id text NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  display_name text NOT NULL,
  slug text NOT NULL,
  contact_type text NOT NULL DEFAULT 'department',
  phone_e164 text,
  phone_ext text,
  email text,
  sms_enabled boolean NOT NULL DEFAULT true,
  email_enabled boolean NOT NULL DEFAULT false,
  can_transfer boolean NOT NULL DEFAULT true,
  notify_message boolean NOT NULL DEFAULT false,
  notify_rdv boolean NOT NULL DEFAULT false,
  notify_transfer_fail boolean NOT NULL DEFAULT true,
  keywords text[] NOT NULL DEFAULT '{}',
  priority integer NOT NULL DEFAULT 100,
  active boolean NOT NULL DEFAULT true,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT client_contacts_client_slug_unique UNIQUE (client_id, slug)
);

CREATE INDEX IF NOT EXISTS client_contacts_client_id_idx
  ON public.client_contacts (client_id);

CREATE INDEX IF NOT EXISTS client_contacts_client_active_idx
  ON public.client_contacts (client_id, active)
  WHERE active = true;

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.set_client_contacts_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS client_contacts_set_updated_at ON public.client_contacts;
CREATE TRIGGER client_contacts_set_updated_at
  BEFORE UPDATE ON public.client_contacts
  FOR EACH ROW
  EXECUTE FUNCTION public.set_client_contacts_updated_at();

-- ---------------------------------------------------------------------------
-- Migrate existing clients.transfer_numbers JSON -> client_contacts
-- (idempotent: skip if slug already exists for client)
-- ---------------------------------------------------------------------------

INSERT INTO public.client_contacts (
  client_id,
  display_name,
  slug,
  contact_type,
  phone_e164,
  can_transfer,
  notify_transfer_fail,
  priority,
  active
)
SELECT
  c.id AS client_id,
  trim(e.key) AS display_name,
  trim(
    both '-'
    from lower(
      regexp_replace(
        regexp_replace(
          translate(
            trim(e.key),
            'éèêëàâäùûüôöîïçÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ',
            'eeeeaaauuuooiieeeeaaauuuooiic'
          ),
          '[^a-zA-Z0-9]+',
          '-',
          'g'
        ),
        '-+',
        '-',
        'g'
      )
    )
  ) AS slug,
  'department' AS contact_type,
  trim(e.value) AS phone_e164,
  true AS can_transfer,
  true AS notify_transfer_fail,
  100 AS priority,
  true AS active
FROM public.clients c
CROSS JOIN LATERAL jsonb_each_text(COALESCE(c.transfer_numbers, '{}'::jsonb)) AS e(key, value)
WHERE trim(e.key) <> ''
  AND trim(e.value) <> ''
  AND NOT EXISTS (
    SELECT 1
    FROM public.client_contacts cc
    WHERE cc.client_id = c.id
      AND cc.slug = trim(
        both '-'
        from lower(
          regexp_replace(
            regexp_replace(
              translate(
                trim(e.key),
                'éèêëàâäùûüôöîïçÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ',
            'eeeeaaauuuooiieeeeaaauuuooiic'
              ),
              '[^a-zA-Z0-9]+',
              '-',
              'g'
            ),
            '-+',
            '-',
            'g'
          )
        )
      )
  );

-- ---------------------------------------------------------------------------
-- Row Level Security (dashboard read; agent writes via service_role)
-- ---------------------------------------------------------------------------

ALTER TABLE public.client_contacts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS client_contacts_select_admin ON public.client_contacts;
CREATE POLICY client_contacts_select_admin
  ON public.client_contacts
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

DROP POLICY IF EXISTS client_contacts_select_client ON public.client_contacts;
CREATE POLICY client_contacts_select_client
  ON public.client_contacts
  FOR SELECT
  TO authenticated
  USING (client_id = public.current_user_client_id());

DROP POLICY IF EXISTS client_contacts_insert_admin ON public.client_contacts;
CREATE POLICY client_contacts_insert_admin
  ON public.client_contacts
  FOR INSERT
  TO authenticated
  WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS client_contacts_update_admin ON public.client_contacts;
CREATE POLICY client_contacts_update_admin
  ON public.client_contacts
  FOR UPDATE
  TO authenticated
  USING (public.is_admin())
  WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS client_contacts_delete_admin ON public.client_contacts;
CREATE POLICY client_contacts_delete_admin
  ON public.client_contacts
  FOR DELETE
  TO authenticated
  USING (public.is_admin());

GRANT SELECT ON public.client_contacts TO authenticated, service_role;
GRANT INSERT, UPDATE, DELETE ON public.client_contacts TO service_role;

