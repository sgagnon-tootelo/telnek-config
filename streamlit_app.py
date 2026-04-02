import streamlit as st
import json
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
from streamlit_autorefresh import st_autorefresh
import plotly.express as px

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

    # ====================== TABS PRINCIPAUX ======================
    tab_global, tab_config, tab_appels, tab_stats = st.tabs([
        "🌍 Dashboard Global (tous les clients)",
        "⚙️ Configuration client",
        "📞 Historique des appels",
        "📊 Statistiques"
    ])

    # ====================== TAB DASHBOARD GLOBAL (avec stats cumulatives – CORRIGÉ) ======================
    with tab_global:
        st.subheader("🌍 Dashboard Global – Tous les clients")
        
        auto_refresh = st.toggle("🔄 Rafraîchissement automatique toutes les 5 secondes", 
                                value=True, key="global_refresh")
        
        if auto_refresh:
            st_autorefresh(interval=5000, limit=300, key="global_auto")

        # ====================== APPELS EN COURS (live) ======================
        live_response = supabase.table('vw_appels_clients') \
            .select('client_id, company_name, call_date, call_time, caller_number, room_name, status_label, started_at') \
            .eq('status', 'in_progress') \
            .order('started_at', desc=True) \
            .execute()
        
        if live_response.data:
            df_global = pd.DataFrame(live_response.data)
            
            tz_montreal = pytz.timezone('America/Montreal')
            now = datetime.now(tz_montreal)
            
            df_global['started_at'] = pd.to_datetime(df_global['started_at'])
            if df_global['started_at'].dt.tz is None:
                df_global['started_at'] = df_global['started_at'].dt.tz_localize('UTC')
            df_global['started_at'] = df_global['started_at'].dt.tz_convert(tz_montreal)
            
            df_global['Durée en cours'] = df_global['started_at'].apply(
                lambda x: str(now - x).split('.')[0] + " min" if (now - x).total_seconds() > 60 else "Moins d'1 min"
            )
            
            display_cols = ['company_name', 'call_date', 'call_time', 'caller_number', 'Durée en cours', 'room_name']
            styled = df_global[display_cols].style.apply(
                lambda row: ['background-color: #d4edda'] * len(row) if 'min' in str(row['Durée en cours']) else [''] * len(row),
                axis=1
            )
            
            st.dataframe(styled, use_container_width=True, hide_index=True)
            st.metric("📞 TOTAL appels en cours (tous clients)", len(df_global))
        else:
            st.success("✅ Aucun appel en cours. Tout est calme dans l’empire Amélie ! 😌")

        # ====================== DERNIER APPEL REÇU (GLOBAL) ======================
        st.divider()
        st.subheader("🕒 Dernier appel reçu – Tous les clients")

        latest_response = supabase.table('vw_appels_clients') \
            .select('started_at, company_name, caller_number, status_label') \
            .order('started_at', desc=True) \
            .limit(1) \
            .execute()

        if latest_response.data:
            last = latest_response.data[0]
            
            tz_montreal = pytz.timezone('America/Montreal')
            last_time = pd.to_datetime(last['started_at'])
            if last_time.tz is None:
                last_time = last_time.tz_localize('UTC')
            last_time = last_time.tz_convert(tz_montreal)
            
            formatted_time = last_time.strftime("%d %B %Y à %H:%M:%S")
            
            st.metric(
                label="🕒 Dernier appel reçu",
                value=formatted_time,
                delta=f"{last.get('company_name', 'Inconnu')} • {last.get('caller_number', 'N/A')}"
            )
            st.caption(f"**Statut :** {last.get('status_label', '—')}")
        else:
            st.info("Aucun appel enregistré pour le moment.")
            
        # ====================== STATS CUMULATIVES GLOBALES (FIX KeyError) ======================
        st.divider()
        st.subheader("📊 Statistiques cumulatives – Tous les clients")

        stats_response = supabase.table('vw_stats_appels_clients').select('*').execute()
        
        if stats_response.data:
            df_stats = pd.DataFrame(stats_response.data)
            
            # === FIX : on récupère les noms d'entreprise via get_clients() ===
            clients_list = get_clients()
            client_map = {c['id']: c.get('company_name', c['id']) for c in clients_list}
            df_stats['company_name'] = df_stats['client_id'].map(client_map).fillna('Inconnu')

            # Calculs globaux
            total_appels = int(df_stats['total_appels'].sum())
            completes = int(df_stats['appels_completes'].sum())
            rdv_reserves = int(df_stats['rdv_reserves'].sum())
            duree_moyenne = round(df_stats['duree_moyenne_sec'].mean(), 1) if not df_stats.empty else 0

            # Comptes spéciaux
            abandoned_resp = supabase.table('vw_appels_clients').select("*", count="exact").eq('status', 'abandoned').execute()
            confirmed_resp = supabase.table('vw_appels_clients').select("*", count="exact").eq('appointment_confirmed', True).execute()
            cancelled_resp = supabase.table('vw_appels_clients').select("*", count="exact").eq('appointment_cancelled', True).execute()

            appels_abandonnes = abandoned_resp.count or 0
            rdv_confirmes = confirmed_resp.count or 0
            rdv_annules = cancelled_resp.count or 0

            # Métriques
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            with col1: st.metric("📞 Total appels", total_appels)
            with col2: st.metric("✅ Complétés", completes)
            with col3: st.metric("📅 RDV réservés", rdv_reserves)
            with col4: st.metric("⏱️ Durée moyenne", f"{duree_moyenne} s")
            with col5: st.metric("📵 Abandonnés", appels_abandonnes)
            with col6: st.metric("✅ RDV Confirmés", rdv_confirmes)
            with col7: st.metric("❌ RDV Annulés", rdv_annules)

            # Tableau récap par client + ligne TOTAL
            df_stats_display = df_stats[['company_name', 'total_appels', 'appels_completes', 'rdv_reserves', 'duree_moyenne_sec']].copy()
            df_stats_display = df_stats_display.rename(columns={
                'company_name': 'Client',
                'total_appels': 'Total appels',
                'appels_completes': 'Complétés',
                'rdv_reserves': 'RDV réservés',
                'duree_moyenne_sec': 'Durée moy. (s)'
            })
            df_stats_display.loc[len(df_stats_display)] = ['TOTAL', total_appels, completes, rdv_reserves, duree_moyenne]
            
            st.dataframe(df_stats_display.style.set_properties(subset=['Client'], **{'font-weight': 'bold'}), 
                        use_container_width=True, hide_index=True)
        else:
            st.info("Aucune statistique disponible pour le moment.")
                        
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

        col1, col2 = st.columns(2)

        with col1:
            get_caller_history_flag = st.toggle(
                "Activé mémoire de l'appelant", 
                value=client.get('get_caller_history_flag', False)
            )

        with col2:
            call_transcription_flag = st.toggle(
                "Activé la transcription de l'appel", 
                value=client.get('call_transcription_flag', False)
            )

        # Optionnel : petit feedback visuel
        if get_caller_history_flag:
            st.caption("→ Mémoire de l'appelant activée")
        if call_transcription_flag:
            st.caption("→ Transcription des appels activée")

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
                'transfer_numbers': transfer_numbers_parsed,
                'get_caller_history_flag': get_caller_history_flag,
                'call_transcription_flag': call_transcription_flag
            }
            update_client(selected_client_id, updated_data)
            st.success("✅ Configuration sauvegardée avec succès !")
            st.rerun()

    # ====================== TAB HISTORIQUE DES APPELS + ÉCOUTE WAV (MIS À JOUR) ======================
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
            
            # Format Montréal (version robuste)
            tz_montreal = pytz.timezone('America/Montreal')
            for col in ['started_at', 'appointment_start']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    mask = df[col].notna()
                    if mask.any():
                        if df.loc[mask, col].dt.tz is None:
                            df.loc[mask, col] = df.loc[mask, col].dt.tz_localize('UTC')
                        df.loc[mask, col] = df.loc[mask, col].dt.tz_convert(tz_montreal)
                                    
            # ====================== NOUVEAU : STATUT RDV ======================
            def get_rdv_status(row):
                if not row.get('appointment_booked', False):
                    return "—"
                elif row.get('appointment_cancelled', False):
                    return "❌ Annulé"
                elif row.get('appointment_confirmed', False):
                    return "✅ Confirmé"
                else:
                    return "⏳ À confirmer"

            df['statut_rdv'] = df.apply(get_rdv_status, axis=1)

            def color_rdv_status(val):
                if "Confirmé" in str(val):
                    return 'background-color: #d4edda; color: #155724'
                elif "Annulé" in str(val):
                    return 'background-color: #f8d7da; color: #721c24'
                elif "À confirmer" in str(val):
                    return 'background-color: #fff3cd; color: #856404'
                return ''

            # Aperçu transcription + indicateur audio
            df['transcript_preview'] = df['transcript'].fillna('').astype(str).apply(
                lambda x: (x[:85] + '...') if len(x) > 85 else x
            )
            df['🎧'] = df.apply(
                lambda row: '✅' if any(pd.notna(row.get(col)) for col in ['recording_url', 'audio_url', 'wav_url', 'recording']) else '',
                axis=1
            )

            # Colonnes du tableau
            display_columns = [
                'call_date', 'call_time', 'caller_number',
                '🎧', 'status_label', 'statut_rdv',
                'appointment_start', 'appointment_name', 'duration_formatted',
                'transcript_preview'
            ]
            available_cols = [col for col in display_columns if col in df.columns]
            
            def highlight_rdv(row):
                if row.get('appointment_booked'):
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)
            
            styled_df = df[available_cols].style.apply(highlight_rdv, axis=1)
            styled_df = styled_df.map(color_rdv_status, subset=['statut_rdv'])
            
            st.caption("👇 Clique sur une ligne pour afficher la transcription + écouter l’enregistrement")
            event = st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"call_table_{selected_client_id}"
            )
            
            # Téléchargement CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger en CSV", csv, 
                             f"appels_{selected_client_id}.csv", "text/csv")

            # ====================== DÉTAIL SÉLECTIONNÉ ======================
            if event.selection.rows:
                row = df.iloc[event.selection.rows[0]]
                
                st.divider()
                st.subheader(f"🔊 Appel du {row.get('call_date')} {row.get('call_time')} — {row.get('caller_number')}")
                
                # Statut RDV en évidence
                st.markdown(f"**Statut du rendez-vous :** {row.get('statut_rdv', '—')}")

                # === LECTEUR AUDIO ===
                st.subheader("🎧 Enregistrement de l'appel")
                recording_url = row.get('recording_url')
                if recording_url and isinstance(recording_url, str) and recording_url.startswith('http'):
                    try:
                        account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
                        auth_token = st.secrets["TWILIO_AUTH_TOKEN"]
                        response = requests.get(recording_url, auth=(account_sid, auth_token), timeout=15)
                        if response.status_code == 200:
                            audio_bytes = response.content
                            st.success("✅ Enregistrement chargé avec succès")
                            st.audio(audio_bytes, format="audio/wav")
                            st.download_button(
                                label="📥 Télécharger l'enregistrement WAV",
                                data=audio_bytes,
                                file_name=f"appel_{row.get('caller_number','inconnu')}_{row.get('call_date','')}.wav",
                                mime="audio/wav"
                            )
                        else:
                            st.error(f"❌ Twilio a refusé l'accès (code {response.status_code})")
                    except Exception as e:
                        st.error(f"Erreur lors du chargement : {str(e)}")
                else:
                    st.info("🔇 Aucun enregistrement disponible pour cet appel.")
                
                # === TRANSCRIPTION ===
                st.subheader("📝 Transcription complète")
                transcript = row.get('transcript', '')
                if transcript and str(transcript).strip():
                    st.text_area("Transcription complète", transcript, height=380)
                else:
                    st.info("Aucune transcription disponible.")
            else:
                st.info("Sélectionne une ligne dans le tableau ci-dessus.")
                
        else:
            st.info("Aucun appel enregistré pour le moment.")

# ====================== TAB STATISTIQUES – VERSION OPTIMISÉE + TRANSFERTS & MESSAGES ======================
with tab_stats:
    st.subheader(f"📊 Statistiques détaillées – {selected_client_id}")
    
    # 1. Métriques rapides depuis la vue agrégée
    stats_response = supabase.table('vw_stats_appels_clients') \
        .select('*') \
        .eq('client_id', selected_client_id) \
        .execute()
    
    if stats_response.data and len(stats_response.data) > 0:
        stats_df = pd.DataFrame(stats_response.data).iloc[0]
        
        total = int(stats_df['total_appels'])
        completes = int(stats_df['appels_completes'])
        booked = int(stats_df['rdv_reserves'])
        confirmed = int(stats_df.get('rdv_confirmes', 0))
        cancelled = int(stats_df.get('rdv_annules', 0))
        duree_moy = float(stats_df['duree_moyenne_sec'])
        pourcent_rdv = float(stats_df['pourcentage_rdv'])
        
        taux_confirmation = (confirmed / (confirmed + cancelled) * 100) if (confirmed + cancelled) > 0 else 0
        appels_abandonnes = total - completes
        taux_abandon = (appels_abandonnes / total * 100) if total > 0 else 0

        # ====================== NOUVELLES MÉTRIQUES : TRANSFERTS & MESSAGES ======================
        # On va chercher les détails seulement pour ces nouveaux calculs + graphiques
        appels_response = supabase.table('vw_appels_clients') \
            .select('*') \
            .eq('client_id', selected_client_id) \
            .execute()
        
        transferred = 0
        transferred_success = 0
        messages_pris = 0
        
        if appels_response.data:
            df_detail = pd.DataFrame(appels_response.data)
            transferred = len(df_detail[df_detail['transfer_attempted'] == True])
            transferred_success = len(df_detail[df_detail['transfer_success'] == True])
            messages_pris = len(df_detail[df_detail['message_taken'] == True])

        # Métriques (maintenant 2 rangées pour rester beau)
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        with col1: st.metric("📞 Total appels", total)
        with col2: st.metric("✅ Complétés", completes)
        with col3: st.metric("📅 RDV réservés", booked, delta=f"{pourcent_rdv:.1f}%")
        with col4: st.metric("✅ RDV confirmés", confirmed)
        with col5: st.metric("❌ RDV annulés", cancelled)
        with col6: st.metric("📵 Abandonnés", appels_abandonnes, delta=f"{taux_abandon:.1f}%")
        with col7: st.metric("⏱️ Durée moyenne", f"{duree_moy:.1f} s")
        with col8: st.metric("🎯 Taux confirmation RDV", f"{taux_confirmation:.1f}%")

        # Deuxième rangée pour les nouveaux stats
        st.divider()
        colA, colB, colC, colD = st.columns(4)
        with colA: st.metric("🔄 Appels transférés (tentés)", transferred)
        with colB: st.metric("✅ Transferts réussis", transferred_success, 
                            delta=f"{(transferred_success / transferred * 100) if transferred > 0 else 0:.1f}%")
        with colC: st.metric("📩 Messages pris", messages_pris)
        with colD: st.metric("📞 Appels normaux", total - transferred - messages_pris)

        st.caption(f"**Funnel :** {total} appels → {booked} RDV → {confirmed} confirmés | {transferred} transférés | {messages_pris} messages")

        # ====================== GRAPHES PLOTLY ======================
        st.divider()
        st.subheader("📈 Visualisations")

        col_g1, col_g2 = st.columns(2)

        # Pie : Répartition Transfert / Message / Normal
        with col_g1:
            repartition = pd.DataFrame({
                "Type": ["Appels normaux", "Appels transférés", "Messages pris"],
                "Nombre": [total - transferred - messages_pris, transferred, messages_pris]
            })
            fig_pie = px.pie(repartition, values="Nombre", names="Type",
                           title="Répartition des types d'appels",
                           color_discrete_sequence=px.colors.sequential.Blues)
            st.plotly_chart(fig_pie, use_container_width=True)

        # Bar : Top motifs de RDV (comme avant)
        with col_g2:
            if appels_response.data and 'appointment_reason' in df_detail.columns:
                reasons = df_detail[df_detail['appointment_booked'] == True]['appointment_reason'].value_counts().head(8)
                fig_bar = px.bar(x=reasons.index, y=reasons.values,
                               labels={"x": "Motif du RDV", "y": "Nombre"},
                               title="Top 8 des motifs de rendez-vous")
                st.plotly_chart(fig_bar, use_container_width=True)

        # ====================== TABLEAU DÉTAILLÉ (ajout colonnes transfert & message) ======================
        st.divider()
        st.subheader("📋 Détail par appel")
        
        df_display = df_detail[['call_date', 'call_time', 'caller_number', 'status',
                               'transfer_attempted', 'transfer_success', 'message_taken',
                               'appointment_booked', 'appointment_confirmed', 'appointment_reason']].copy()
        
        def color_row(row):
            if row['appointment_confirmed']:
                return ['background-color: #d4edda'] * len(row)
            elif row['appointment_cancelled']:
                return ['background-color: #f8d7da'] * len(row)
            elif row['transfer_success'] is True:
                return ['background-color: #fff3cd'] * len(row)
            return [''] * len(row)
        
        styled = df_display.style.apply(color_row, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Export CSV
        csv = df_detail.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger tout en CSV", csv, 
                         f"stats_detaillees_{selected_client_id}.csv", "text/csv")
    
    else:
        st.info("Aucune statistique disponible pour ce client pour l’instant.")