import streamlit as st
import json
import pandas as pd
from supabase import create_client, Client

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

    # ====================== 3 TABS COMME AVANT ======================
    tab_config, tab_appels, tab_stats = st.tabs([
        "⚙️ Configuration", 
        "📞 Historique des appels", 
        "📊 Statistiques"
    ])

    # ====================== TAB CONFIGURATION ======================
    with tab_config:
        st.subheader(f"Paramètres pour {selected_client_id}")
        
        company_name = st.text_input("Nom de l'entreprise", value=client.get('company_name', ''))
        company_address = st.text_input("Adresse de l'entreprise", value=client.get('company_address', ''))
        company_hours = st.text_input("Heures d'ouverture (texte affiché)", value=client.get('company_hours', ''))
        
        # === HORAIRES NUMÉRIQUES ===
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
        
        # url_map avec validation
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
        
        # Voix
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

        # Mode transfert
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

        # Transfer numbers avec validation
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

        # ====================== BOUTON SAUVEGARDER ======================
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
            .limit(300) \
            .execute()
        
        if appels_response.data:
            df = pd.DataFrame(appels_response.data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger en CSV", csv, 
                             f"appels_{selected_client_id}.csv", "text/csv")
        else:
            st.info("Aucun appel enregistré pour le moment.")

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
            with col1: st.metric("Total appels", int(stats_df['total_appels'].iloc[0]))
            with col2: st.metric("Appels complétés", int(stats_df['appels_completes'].iloc[0]))
            with col3: st.metric("Durée moyenne", f"{stats_df['duree_moyenne_sec'].iloc[0]:.1f} s")
            with col4: st.metric("Transferts réussis", int(stats_df['transferts_reussis'].iloc[0]))
        else:
            st.info("Aucune statistique disponible pour ce client.")
