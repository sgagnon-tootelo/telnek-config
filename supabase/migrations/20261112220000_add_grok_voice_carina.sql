-- Voix Grok Carina (douce, empathique) dans le sélecteur de l'interface.
INSERT INTO public.voices (provider, voice_key, display_label, tts_model, is_active, sort_order)
SELECT 'grok', 'carina', 'Carina – Féminine douce et empathique', NULL, true, 60
WHERE NOT EXISTS (
  SELECT 1
  FROM public.voices
  WHERE provider = 'grok'
    AND voice_key = 'carina'
);
