import streamlit as st
import json
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
from google_auth_oauthlib.flow import InstalledAppFlow

# ==================== CONNEXION SUPABASE ====================
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# ==================== FONCTIONS HELPER ====================
def get_clients():
    return supabase.table('clients').select('*').execute().data

def update_client(client_id, data):
    return supabase.table('clients').update(data).eq('id', client_id).execute()

# ==================== INTERFACE ====================
st.set_page_config(page_title="Amélie - Telnek AI", page_icon="📞", layout="wide")
st.title("📞 Telnek – AI Agent de Réception Virtuel")

# Sélection du client
clients = get_clients()
if not clients:
    st.error("Aucun client trouvé.")
    st.stop()

clients_sorted = sorted(clients, key=lambda c: c['id'].lower())
client_options = {c['id']: c['id'] for c in clients_sorted}
selected_client_id = st.selectbox("Sélectionnez un client", list(client_options.keys()))

if selected_client_id:
    client = next(c for c in clients if c['id'] == selected_client_id)

    tab_config, tab_appels, tab_stats = st.tabs([
        "⚙️ Configuration", 
        "📞 Historique des appels", 
        "📊 Statistiques"
    ])

    # ====================== TAB CONFIGURATION (identique à ta version) ======================
    with tab_config:
        st.subheader(f"Paramètres pour {selected_client_id}")
        
        company_name = st.text_input("Nom de l'entreprise", value=client.get('company_name', ''))
        company_address = st.text_input("Adresse de l'entreprise", value=client.get('company_address', ''))
        company_hours = st.text_input("Heures d'ouverture (texte affiché)", value=client.get('company_hours', ''))
        
        col1, col2 = st.columns(2)
        with col1:
            opening_hour = st.number_input("🕒 Heure d'ouverture (0-23)", 
                                         value=client.get('opening_hour', 9), min_value=0, max_value=23, step=1)
        with col2:
            closing_hour = st.number_input("🕒 Heure de fermeture (1-24)", 
                                         value=client.get('closing_hour', 17), min_value=1, max_value=24, step=1)

        admin_phone = st.text_input("Numéro SMS (messages & transferts refusés)", value=client.get('admin_phone', ''))
        callee_number = st.text_input("Numéro de l'agent virtuel", value=client.get('callee_number', ''), disabled=True)
        
        instructions_specific = st.text_area("Instructions spécifiques de l'entreprise", 
                                           value=client.get('instructions_specific', ''), height=120)
        
        base_url = st.text_input("Site Web de l'entreprise", value=client.get('base_url', ''))
        
        url_map_str = json.dumps(client.get('url_map', {}) or {}, indent=4, ensure_ascii=False)
        url_map_edited = st.text_area("Sujets associés sur le site Web (format JSON)", 
                                      value=url_map_str, height=150)
        if st.button("✅ Valider le JSON (url_map)"):
            try:
                json.loads(url_map_edited)
                st.success("✅ JSON url_map valide !")
                st.json(json.loads(url_map_edited))
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON invalide : {e}")

        agent_name = st.text_input("Nom de l'agent", value=client.get('agent_name', 'Amélie'))
        
        voice_options = [
            {"value": "ara", "label": "Ara – Féminine, chaleureuse (défaut)"},
            {"value": "eve", "label": "Eve – Féminine énergique"},
            {"value": "leo", "label": "Leo – Masculin autoritaire"},
            {"value": "rex", "label": "Rex – Masculin professionnel"},
            {"value": "sal", "label": "Sal – Neutre polyvalent"}
        ]
        current_voice = client.get('voice_name', 'ara')
        default_index = next((i for i, opt in enumerate(voice_options) if opt["value"] == current_voice), 0)
        selected_voice = st.selectbox("Voix de l'agent", options=voice_options, 
                                      format_func=lambda x: x["label"], index=default_index)
        voice_name = selected_voice["value"]

        transfer_mode_options = [
            {"value": "blind", "label": "Blind – Transfert immédiat"},
            {"value": "warm",  "label": "Warm  – Transfert supervisé"},
            {"value": "none",  "label": "None  – Aucun transfert"},
        ]
        current_mode = client.get('transfer_mode', 'none')
        default_mode_index = next((i for i, opt in enumerate(transfer_mode_options) if opt["value"] == current_mode), 2)
        selected_mode = st.selectbox("Mode de transfert", options=transfer_mode_options, 
                                     format_func=lambda x: x["label"], index=default_mode_index)
        transfer_mode_selected = selected_mode["value"]

        if transfer_mode_selected != "none":
            st.subheader("Numéros de transfert")
            transfer_numbers_str = json.dumps(client.get('transfer_numbers', {}) or {}, indent=4, ensure_ascii=False)
            transfer_numbers_edited = st.text_area("Numéros de transfert (JSON)", 
                                                 value=transfer_numbers_str, height=150)
            if st.button("✅ Valider le JSON des transferts"):
                try:
                    json.loads(transfer_numbers_edited)
                    st.success("✅ JSON des transferts valide !")
                    st.json(json.loads(transfer_numbers_edited))
                except json.JSONDecodeError as e:
                    st.error(f"❌ JSON invalide : {e}")

        # ====================== GOOGLE CALENDAR (identique à ta version) ======================
        st.subheader("📅 Connexion Google Calendar")
        fresh_client = next((c for c in get_clients() if c['id'] == selected_client_id), client)
        current_token = fresh_client.get('google_refresh_token')
        has_google = bool(current_token)

        col_connect, col_disconnect = st.columns([3, 2])
        with col_connect:
            if has_google:
                st.success("✅ Calendrier Google **connecté**")
            else:
                if st.button("🔗 Connecter le calendrier Google de ce client", type="primary"):
                    SCOPES = ['https://www.googleapis.com/auth/calendar']
                    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", scopes=SCOPES)
                    credentials = flow.run_local_server(port=8502, prompt='consent')
                    if credentials and credentials.refresh_token:
                        supabase.table("clients").update({"google_refresh_token": credentials.refresh_token}).eq("id", selected_client_id).execute()
                        st.success("🎉 Calendrier connecté !")
                        st.rerun()
                    else:
                        st.error("Aucun refresh_token reçu.")

        with col_disconnect:
            if has_google:
                if st.button("❌ Dissocier le lien Google Calendar", type="secondary"):
                    supabase.table("clients").update({"google_refresh_token": None}).eq("id", selected_client_id).execute()
                    st.success("🎉 Token supprimé avec succès !")
                    st.rerun()

        if st.button("💾 Sauvegarder la configuration", type="primary"):
            try:
                url_map_parsed = json.loads(url_map_edited) if url_map_edited.strip() else {}
            except:
                st.error("JSON url_map invalide")
                st.stop()

            transfer_numbers_parsed = {}
            if transfer_mode_selected != "none":
                try:
                    transfer_numbers_parsed = json.loads(transfer_numbers_edited) if transfer_numbers_edited.strip() else {}
                except:
                    st.error("JSON transfer_numbers invalide")
                    st.stop()
            else:
                transfer_numbers_parsed = client.get('transfer_numbers', {}) or {}

            updated_data = {
                'company_name': company_name,
                'company_address': company_address,
                'company_hours': company_hours,
                'opening_hour': opening_hour,
                'closing_hour': closing_hour,
                'admin_phone': admin_phone,
                'instructions_specific': instructions_specific,
                'base_url': base_url,
                'url_map': url_map_parsed,
                'agent_name': agent_name,
                'voice_name': voice_name,
                'transfer_mode': transfer_mode_selected,
                'transfer_numbers': transfer_numbers_parsed
            }
            update_client(selected_client_id, updated_data)
            st.success("✅ Configuration sauvegardée avec succès !")
            st.rerun()

    # ====================== TAB HISTORIQUE DES APPELS ======================
    with tab_appels:
        st.subheader(f"📞 Historique des appels – {selected_client_id}")
        
        appels_response = supabase.table('vw_appels_clients') \
            .select('*') \
            .eq('client_id', selected_client_id) \
            .order('started_at', desc=True) \
            .limit(500) \
            .execute()
        
        if appels_response.data:
            df = pd.DataFrame(appels_response.data)
            
            # Format Montréal
            tz_montreal = pytz.timezone('America/Montreal')
            for col in ['started_at', 'appointment_start']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    if df[col].dt.tz is None:
                        df[col] = df[col].dt.tz_localize('UTC')
                    df[col] = df[col].dt.tz_convert(tz_montreal)
            
            # === TRANSCRIPTION DISPONIBLE DIRECTEMENT DANS LA TABLE ===
            # Aperçu court (85 caractères) qui apparaît dans le tableau
            df['transcript_preview'] = df['transcript'].fillna('').astype(str).apply(
                lambda x: (x[:85] + '...') if len(x) > 85 else x
            )

            # Colonnes affichées (la transcription est maintenant dedans !)
            display_columns = [
                'call_date', 'call_time', 'caller_number',
                'status_label', 'appointment_status_badge',
                'appointment_start', 'appointment_name',
                'appointment_reason', 'duration_formatted',
                'transfer_status', 'message_reason', 'message_name',
                'transcript_preview'          # ← maintenant intégré dans la table
            ]
            available_cols = [col for col in display_columns if col in df.columns]
            
            # Style vert pour les RDV
            def highlight_rdv(row):
                if row.get('appointment_booked'):
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)
            
            styled_df = df[available_cols].style.apply(highlight_rdv, axis=1)
            
            # Tableau interactif + sélection de ligne
            st.caption("👇 Clique sur une ligne du tableau pour voir la **transcription complète**")
            event = st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"call_table_{selected_client_id}"   # évite les conflits de clé
            )
            
            # Bouton CSV (inclut la transcription complète)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger en CSV", csv, 
                             f"appels_{selected_client_id}.csv", "text/csv")

            # ====================== TRANSCRIPTION DE L'APPEL SÉLECTIONNÉ ======================
            if event.selection.rows:
                selected_idx = event.selection.rows[0]
                row = df.iloc[selected_idx]
                
                st.divider()
                st.subheader(f"🔊 Transcription complète — {row.get('call_date')} {row.get('call_time')} ({row.get('caller_number')})")
                
                transcript = row.get('transcript', '')
                if transcript and str(transcript).strip():
                    st.text_area("Transcription complète", transcript, height=420, key="full_trans")
                    
                    # Version structurée par locuteur
                    transcript_json = row.get('transcript_json')
                    if transcript_json and isinstance(transcript_json, list):
                        with st.expander("👥 Voir par locuteur"):
                            for segment in transcript_json[:30]:
                                speaker = segment.get('speaker', 'Inconnu')
                                text = segment.get('text', '')
                                st.markdown(f"**{speaker}** : {text}")
                else:
                    st.info("Aucune transcription disponible pour cet appel.")
            else:
                st.info("Sélectionne une ligne dans le tableau ci-dessus pour afficher la transcription complète.")
                
        else:
            st.info("Aucun appel enregistré pour le moment.")

    # ====================== TAB STATISTIQUES (avec appels abandonnés) ======================
    with tab_stats:
        st.subheader(f"📊 Statistiques – {selected_client_id}")
        stats_response = supabase.table('vw_stats_appels_clients') \
            .select('*') \
            .eq('client_id', selected_client_id) \
            .execute()
        
        if stats_response.data and len(stats_response.data) > 0:
            stats_df = pd.DataFrame(stats_response.data)
            
    # ====================== TAB STATISTIQUES - Appels abandonnés EXACTS ======================
    with tab_stats:
        st.subheader(f"📊 Statistiques – {selected_client_id}")
        
        stats_response = supabase.table('vw_stats_appels_clients') \
            .select('*') \
            .eq('client_id', selected_client_id) \
            .execute()
        
        if stats_response.data and len(stats_response.data) > 0:
            stats_df = pd.DataFrame(stats_response.data)
            
            total = int(stats_df['total_appels'].iloc[0])
            completes = int(stats_df['appels_completes'].iloc[0])
            
            # ====================== COMPTE PRÉCIS DES ABANDONNÉS ======================
            abandoned_response = supabase.table('vw_appels_clients') \
                .select("*", count="exact") \
                .eq('client_id', selected_client_id) \
                .eq('status', 'abandoned') \
                .execute()
            
            appels_abandonnes = abandoned_response.count or 0
            
            # Métriques (6 colonnes)
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1: 
                st.metric("📞 Total appels", total)
            with col2: 
                st.metric("✅ Appels complétés", completes)
            with col3: 
                st.metric("📅 RDV réservés", int(stats_df['rdv_reserves'].iloc[0]))
            with col4: 
                st.metric("% avec RDV", f"{stats_df['pourcentage_rdv'].iloc[0]:.1f}%")
            with col5: 
                st.metric("⏱️ Durée moyenne", f"{stats_df['duree_moyenne_sec'].iloc[0]:.1f} s")
            with col6: 
                st.metric("📵 Appels abandonnés", appels_abandonnes,
                          delta=f"-{appels_abandonnes}" if appels_abandonnes > 0 else None)

            # Taux d'abandon
            pourcent_abandon = (appels_abandonnes / total * 100) if total > 0 else 0
            st.caption(f"**Taux d'abandon : {pourcent_abandon:.1f}%**")

            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune statistique disponible pour ce client.")