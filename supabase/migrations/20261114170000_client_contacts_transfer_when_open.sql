-- Optional per-contact rule: transfer only while the clinic is open.

ALTER TABLE public.client_contacts
  ADD COLUMN IF NOT EXISTS transfer_when_open_only boolean NOT NULL DEFAULT false;
