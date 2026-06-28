-- Enable per-client Telnek demo pitch (offer_telnek_demo tool in GrokVoiceAgent)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS telnek_demo_enabled BOOLEAN NOT NULL DEFAULT false;

UPDATE clients
SET telnek_demo_enabled = true
WHERE id IN ('avocats', 'electriciens');