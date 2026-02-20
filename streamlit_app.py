import streamlit as st
import json
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
    st.subheader("Configuration des Clients")
    # Créer une liste des noms de clients pour le selectbox (avec ID associé)
    clients_sorted = sorted(clients, key=lambda c: c['company_name'].lower())
    client_options = {client['company_name']: client['id'] for client in clients_sorted}
    selected_client_name = st.selectbox("Sélectionnez un client existant :", list(client_options.keys()))
    
    if selected_client_name:
        # Récupérer les détails du client sélectionné
        selected_client_id = client_options[selected_client_name]
        selected_client = next(client for client in clients if client['id'] == selected_client_id)
        
        # Afficher et éditer les paramètres
        st.subheader(f"Paramètres pour {selected_client_name}")
        
        # Champs éditables (ajoute-en plus si tu as d'autres colonnes)
        company_name = st.text_input("Nom de l'entreprise", value=selected_client.get('company_name', ''))
        company_address = st.text_input("Adresse de l'entreprise", value=selected_client.get('company_address', ''))
        company_hours = st.text_input("Heures ouverture", value=selected_client.get('company_hours', ''))
        admin_phone = st.text_input("Numéro de téléphone pour recevoir les messages textes (SMS)", value=selected_client.get('admin_phone', ''))
        callee_number = st.text_input("Numéro de l'agent virtuel", value=selected_client.get('callee_number', ''), disabled=True, help="Ce numéro est configuré au niveau Twilio et ne peut pas être modifié ici.")
        instructions_specific = st.text_area("Instructions spécifiques de l'entreprise", value=selected_client.get('instructions_specific', ''))
        base_url = st.text_input("Site Web de l'entreprise", value=selected_client.get('base_url', ''))
        
        # Gestion spéciale pour url_map (JSON)
        url_map_json = selected_client.get('url_map', {})  # Récupère comme dict (ou vide si None)
        # Convertit en string prettified pour édition
        url_map_str = json.dumps(url_map_json, indent=4, ensure_ascii=False) if url_map_json else '{}'
        
        #st.subheader("Sujets associés sur le site Web (format JSON)")
        #st.markdown("Exemple : \n```json\n{\n    \"accueil\": \"/\",\n    \"services\": \"/services\",\n    \"contact\": \"/nous-joindre\"\n}\n```")
        
        url_map_edited = st.text_area(
            "Sujets associés sur le site Web (format JSON)", 
            value=url_map_str, 
            height=200,  # Hauteur plus grande pour confort
            placeholder='{"accueil": "/", "services": "/services"}'
        )
        
        # Bouton optionnel pour valider le JSON en live
        if st.button("Valider le JSON (optionnel)"):
            try:
                json.loads(url_map_edited)
                st.success("JSON valide !")
                st.json(json.loads(url_map_edited), expanded=True)  # Preview interactif
            except json.JSONDecodeError as e:
                st.error(f"JSON invalide : {e}")
        
        agent_name = st.text_input("Nom de l'agent", value=selected_client.get('agent_name', ''))
        
        # Liste des voix disponibles (minuscules, comme attendu par l'API)
        available_voices = ["ara", "eve", "leo", "rex", "sal"]

        # Valeur actuelle (ou "ara" par défaut si vide ou invalide)
        current_voice = selected_client.get('voice_name', 'ara').lower().strip()
        if current_voice not in available_voices:
            current_voice = "ara"  # fallback safe

        voice_name = st.selectbox(
            "Nom de la voix de l'agent",
            options=available_voices,
            index=available_voices.index(current_voice),  # sélectionne la valeur actuelle
            help="Choisissez une voix parmi les options officielles Grok Voice Agent API.\nAra est la voix par défaut (chaleureuse et naturelle)."
        )

        # Bouton pour sauvegarder
        if st.button("Sauvegarder les modifications"):
            # Valider et parser url_map en JSON natif
            try:
                url_map_parsed = json.loads(url_map_edited) if url_map_edited.strip() else {}
            except json.JSONDecodeError as e:
                st.error(f"Impossible de sauvegarder : JSON invalide pour url_map. Erreur : {e}")
                st.stop()

            # Préparer les données à updater
            updated_data = {
                'company_name': company_name,
                'company_address': company_address,
                'company_hours': company_hours,
                'admin_phone': admin_phone,
                'callee_number': callee_number,
                'instructions_specific': instructions_specific,
                'base_url': base_url,
                'url_map': url_map_parsed,  # Envoie comme dict JSON natif !
                'agent_name': agent_name,
                'voice_name': voice_name
                # Ajoute d'autres champs ici si besoin
            }
            
            # Mettre à jour dans Supabase
            update_response = update_client(selected_client_id, updated_data)
            
            if update_response.data:
                st.success("Modifications sauvegardées avec succès ! Le champ url_map est bien stocké comme JSON.")
            else:
                st.error("Erreur lors de la sauvegarde. Vérifiez les logs Supabase ou les permissions (RLS ?).")
