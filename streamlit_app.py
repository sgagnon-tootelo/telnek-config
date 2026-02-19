import streamlit as st
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
st.title("Telnek AI Agent Virtue")

# Récupérer la liste des clients
clients = get_clients()

if not clients:
    st.warning("Aucun client trouvé dans la base de données.")
else:
    st.subheader("Configuration des Clients")
    # Créer une liste des noms de clients pour le selectbox (avec ID associé)
    client_options = {client['company_name']: client['id'] for client in clients}
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
        callee_number = st.text_input("Numéro de l'agent virtuel", value=selected_client.get('callee_number', ''))
        instructions_specific = st.text_area("Instructions spécific de l'entreprise", value=selected_client.get('instructions_specific', ''))
        base_url = st.text_input("Site Web de l'entreprise", value=selected_client.get('base_url', ''))
        url_map = st.text_area("Sujets associés sur le site Web", value=selected_client.get('url_map', ''))
        # Exemple pour d'autres champs : company_email = st.text_input("Email", value=selected_client.get('company_email', ''))
        
        # Bouton pour sauvegarder
        if st.button("Sauvegarder les modifications"):
            # Préparer les données à updater
            updated_data = {
                'company_name': company_name,
                'company_address': company_address,
                'company_hours': company_hours,
                'admin_phone': admin_phone,
                'instructions_specific': instructions_specific,
                'base_url': base_url,
                'url_map': url_map
                # Ajoute d'autres champs ici : 'company_email': company_email,
            }
            
            # Mettre à jour dans Supabase
            update_response = update_client(selected_client_id, updated_data)
            
            if update_response.data:
                st.success("Modifications sauvegardées avec succès !")
            else:
                st.error("Erreur lors de la sauvegarde. Vérifiez les logs ou les permissions.")