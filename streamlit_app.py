import streamlit as st
import json
import pandas as pd
from supabase import create_client, Client

# Connexion à Supabase via secrets
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# Fonction pour récupérer tous les clients
def get_clients():
    response = supabase.table('clients').select('*').execute()
    return response.data

# Fonction pour mettre à jour un client
def update_client(client_id, data):
    response = supabase.table('clients').update(data).eq('id', client_id).execute()
    return response

# Interface Streamlit
st.title("Telnek AI Agent Virtuel")

# Récupérer la liste des clients
clients = get_clients()

if not clients:
    st.warning("Aucun client trouvé dans la base de données.")
else:
    st.subheader("Sélection du Client Id")
    # Créer une liste des noms de clients pour le selectbox
    clients_sorted = sorted(clients, key=lambda c: c['id'].lower())
    client_options = {client['id']: client['id'] for client in clients_sorted}
    selected_client_id = st.selectbox("Sélectionnez un client id existant :", list(client_options.keys()), help="Ce client id est le préfix de la room LiveKit et ne peux pas être modifié")
    
    if selected_client_id:
        selected_client = next((client for client in clients if client['id'] == selected_client_id), None)
        
        # === TABS ===
        tab_config, tab_appels, tab_stats = st.tabs([
            "⚙️ Configuration", 
            "📞 Historique des appels", 
            "📊 Statistiques"
        ])

        selected_client_id = client_options[selected_client_id]

        # ====================== TAB CONFIGURATION ======================
        with tab_config:
            st.subheader(f"Paramètres pour {selected_client_id}")
            
            # Champs éditables (identiques à ton code original)
            company_name = st.text_input("Nom de l'entreprise", value=selected_client.get('company_name', ''))
            company_address = st.text_input("Adresse de l'entreprise", value=selected_client.get('company_address', ''))
            company_hours = st.text_input("Heures ouverture", value=selected_client.get('company_hours', ''))
            admin_phone = st.text_input("Numéro de téléphone pour recevoir les messages textes (SMS)", value=selected_client.get('admin_phone', ''))
            callee_number = st.text_input("Numéro de l'agent virtuel", value=selected_client.get('callee_number', ''), disabled=True, help="Ce numéro est configuré au niveau Twilio et ne peut pas être modifié ici.")
            instructions_specific = st.text_area("Instructions spécifiques de l'entreprise", value=selected_client.get('instructions_specific', ''))
            base_url = st.text_input("Site Web de l'entreprise", value=selected_client.get('base_url', ''))
            
            # url_map JSON
            url_map_json = selected_client.get('url_map', {}) or {}
            url_map_str = json.dumps(url_map_json, indent=4, ensure_ascii=False)
            
            url_map_edited = st.text_area(
                "Sujets associés sur le site Web (format JSON)", 
                value=url_map_str, 
                height=200,
                placeholder='{"accueil": "/", "services": "/services"}'
            )
            
            if st.button("Valider le JSON (url_map)"):
                try:
                    json.loads(url_map_edited)
                    st.success("JSON valide !")
                    st.json(json.loads(url_map_edited))
                except json.JSONDecodeError as e:
                    st.error(f"JSON invalide : {e}")
            
            agent_name = st.text_input("Nom de l'agent", value=selected_client.get('agent_name', ''))
            
            # Voice selection
            voice_options = [
                {"value": "ara", "label": "Ara – Féminine, chaleureuse, amicale (défaut)"},
                {"value": "eve", "label": "Eve – Féminine, énergique, enthousiaste"},
                {"value": "leo", "label": "Leo – Masculin, autoritaire, confiant"},
                {"value": "rex", "label": "Rex – Masculin, professionnel, clair"},
                {"value": "sal", "label": "Sal – Neutre, équilibré, polyvalent"}
            ]
            current_voice = selected_client.get('voice_name', 'ara').lower().strip()
            default_index = next((i for i, opt in enumerate(voice_options) if opt["value"] == current_voice), 0)
            selected_option = st.selectbox(
                "Voix de l'agent virtuel",
                options=voice_options,
                format_func=lambda x: x["label"],
                index=default_index
            )
            voice_name = selected_option["value"]

            # Transfer Mode
            st.subheader("Comportement en cas de demande de transfert")
            transfer_mode_options = [
                {"value": "blind", "label": "Blind – Transfert immédiat (sans supervision)"},
                {"value": "warm",  "label": "Warm  – Transfert supervisé (Amélie parle d'abord)"},
                {"value": "none",  "label": "None  – Aucun transfert – toujours prise de message"},
            ]
            current_mode = selected_client.get('transfer_mode', 'none').lower().strip()
            default_mode_index = next((i for i, opt in enumerate(transfer_mode_options) if opt["value"] == current_mode), 2)
            selected_mode_option = st.selectbox(
                "Mode de transfert",
                options=transfer_mode_options,
                format_func=lambda x: x["label"],
                index=default_mode_index,
                help="Détermine si l'agent virtuel peut transférer l'appel ou doit obligatoirement prendre un message."
            )
            transfer_mode_selected = selected_mode_option["value"]

            # Transfer numbers (seulement si mode != none)
            if transfer_mode_selected != "none":
                st.subheader("Numéros de transfert")
                st.markdown("Format JSON attendu :")
                st.code('{\n    "comptabilité": "+15149474976",\n    "technique": "+15145551234"\n}', language="json")

                transfer_numbers_json = selected_client.get('transfer_numbers', {}) or {}
                transfer_numbers_str = json.dumps(transfer_numbers_json, indent=4, ensure_ascii=False)
                
                transfer_numbers_edited = st.text_area(
                    "Numéros de transfert (JSON)",
                    value=transfer_numbers_str,
                    height=180,
                    placeholder='{\n    "comptabilité": "+15149474976"\n}'
                )

                if st.button("Valider le JSON des transferts"):
                    try:
                        json.loads(transfer_numbers_edited)
                        st.success("✅ JSON des transferts valide !")
                        st.json(json.loads(transfer_numbers_edited))
                    except json.JSONDecodeError as e:
                        st.error(f"❌ JSON invalide : {e}")

            # ====================== BOUTON SAUVEGARDER ======================
            if st.button("💾 Sauvegarder les modifications", type="primary"):
                # Valider JSONs
                try:
                    url_map_parsed = json.loads(url_map_edited) if url_map_edited.strip() else {}
                except json.JSONDecodeError as e:
                    st.error(f"JSON invalide pour url_map : {e}")
                    st.stop()

                transfer_numbers_parsed = {}
                if transfer_mode_selected != "none" and 'transfer_numbers_edited' in locals():
                    try:
                        transfer_numbers_parsed = json.loads(transfer_numbers_edited) if transfer_numbers_edited.strip() else {}
                    except json.JSONDecodeError as e:
                        st.error(f"JSON invalide pour transfer_numbers : {e}")
                        st.stop()

                updated_data = {
                    'company_name': company_name,
                    'company_address': company_address,
                    'company_hours': company_hours,
                    'admin_phone': admin_phone,
                    'callee_number': callee_number,
                    'instructions_specific': instructions_specific,
                    'base_url': base_url,
                    'url_map': url_map_parsed,
                    'agent_name': agent_name,
                    'voice_name': voice_name,
                    'transfer_numbers': transfer_numbers_parsed,
                    'transfer_mode': transfer_mode_selected,
                }
                
                update_response = update_client(selected_client_id, updated_data)
                
                if update_response.data:
                    st.success("✅ Modifications sauvegardées avec succès !")
                    st.rerun()
                else:
                    st.error("Erreur lors de la sauvegarde. Vérifiez les logs ou les permissions RLS.")

        # ====================== TAB HISTORIQUE DES APPELS ======================
        with tab_appels:
            st.subheader(f"📞 Historique des appels – {selected_client_id}")
            
            appels_response = supabase.table('vw_appels_clients') \
                .select('*') \
                .eq('client_id', str(selected_client_id)) \
                .order('started_at', desc=True) \
                .limit(300) \
                .execute()
            
            if appels_response.data:
                df = pd.DataFrame(appels_response.data)
                
                display_columns = [
                    'call_date', 'call_time', 'caller_number',
                    'status_label', 'duration_formatted', 'transfer_status', 
                    'message_status', 'transfer_to_number', 'transfer_client_name', 'transfer_department', 
                    'message_reason', 'message_name', 'message_number'
                ]
                
                available_cols = [col for col in display_columns if col in df.columns]
                st.dataframe(
                    df[available_cols],
                    use_container_width=True,
                    hide_index=True
                )
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Télécharger en CSV",
                    csv,
                    f"appels_{selected_client_id.replace(' ', '_')}.csv",
                    "text/csv"
                )
            else:
                st.info("Aucun appel enregistré pour ce client pour le moment.")

        # ====================== TAB STATISTIQUES ======================
        with tab_stats:
            st.subheader(f"📊 Statistiques – {selected_client_id}")
            
            stats_response = supabase.table('vw_stats_appels_clients') \
                .select('*') \
                .eq('client_id', selected_client_id) \
                .execute()
            
            if stats_response.data and len(stats_response.data) > 0:
                stats_df = pd.DataFrame(stats_response.data)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total appels", int(stats_df['total_appels'].iloc[0]))
                with col2:
                    st.metric("Appels complétés", int(stats_df['appels_completes'].iloc[0]))
                with col3:
                    st.metric("Durée moyenne", f"{stats_df['duree_moyenne_sec'].iloc[0]:.1f} s")
                with col4:
                    st.metric("Transferts réussis", int(stats_df['transferts_reussis'].iloc[0]))
            else:
                st.info("Aucune statistique disponible pour ce client.")