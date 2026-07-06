-- Allow client-role dashboard users to manage their own client_contacts rows.

DROP POLICY IF EXISTS client_contacts_insert_client ON public.client_contacts;
CREATE POLICY client_contacts_insert_client
  ON public.client_contacts
  FOR INSERT
  TO authenticated
  WITH CHECK (client_id = public.current_user_client_id());

DROP POLICY IF EXISTS client_contacts_update_client ON public.client_contacts;
CREATE POLICY client_contacts_update_client
  ON public.client_contacts
  FOR UPDATE
  TO authenticated
  USING (client_id = public.current_user_client_id())
  WITH CHECK (client_id = public.current_user_client_id());

DROP POLICY IF EXISTS client_contacts_delete_client ON public.client_contacts;
CREATE POLICY client_contacts_delete_client
  ON public.client_contacts
  FOR DELETE
  TO authenticated
  USING (client_id = public.current_user_client_id());

GRANT INSERT, UPDATE, DELETE ON public.client_contacts TO authenticated;