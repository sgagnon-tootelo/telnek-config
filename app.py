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
st.title("Configuration des Clients")

# Récupérer la liste des clients
clients = get_clients()

if not clients:
    st.warning("Aucun client trouvé dans la base de données.")
else:
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
        # Exemple pour d'autres champs : company_email = st.text_input("Email", value=selected_client.get('company_email', ''))
        
        # Bouton pour sauvegarder
        if st.button("Sauvegarder les modifications"):
            # Préparer les données à updater
            updated_data = {
                'company_name': company_name,
                'company_address': company_address,
                # Ajoute d'autres champs ici : 'company_email': company_email,
            }
            
            # Mettre à jour dans Supabase
            update_response = update_client(selected_client_id, updated_data)
            
            if update_response.data:
                st.success("Modifications sauvegardées avec succès !")
            else:
                st.error("Erreur lors de la sauvegarde. Vérifiez les logs ou les permissions.")