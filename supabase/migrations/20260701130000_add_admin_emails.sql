-- Fallback courriels admin par client (parallèle à admin_phones pour SMS)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS admin_emails JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN clients.admin_emails IS
'Liste JSON d''adresses courriel admin (fallback take_message si aucun contact email_enabled).';