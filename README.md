# Telnek AI – Interface de Configuration Web

Interface d'administration Streamlit pour gérer les agents virtuels de réception Telnek AI (Amélie et autres voix).

Permet de configurer facilement les profils clients, consulter l'historique des appels, écouter les enregistrements, voir les statistiques et connecter Google Calendar.

![Capture d'écran de l'interface](https://via.placeholder.com/1200x600.png?text=Capture+d%27%C3%A9cran+Telnek+AI+Dashboard)  
*(Ajoute une vraie capture d'écran ici pour rendre le README plus attractif)*

## Fonctionnalités principales

- **Gestion multi-clients** : sélection et configuration de chaque entreprise cliente
- **Paramètres de l'agent** :
  - Nom de l’entreprise, adresse, heures d’ouverture
  - Instructions spécifiques (personnalisation du comportement)
  - Voix de l’agent (Ara, Eve, Leo, Rex, Sal)
  - Modes de transfert (blind, warm, none) + numéros associés
- **Connexion Google Calendar** (OAuth2) pour prise de rendez-vous automatique
- **Historique des appels** :
  - Tableau filtrable et cliquable
  - Aperçu transcription + écoute des enregistrements WAV (proxy sécurisé Twilio)
  - Téléchargement CSV
- **Statistiques** :
  - Total appels, appels complétés, RDV réservés, % RDV, durée moyenne
  - Appels abandonnés + taux d’abandon
  - Mise en évidence visuelle des RDV pris

## Technologies utilisées

- **Frontend** : Streamlit
- **Backend** : Supabase (PostgreSQL + Auth + Storage)
- **Appels & Voix** : Twilio (enregistrements) + LiveKit + Deepgram (transcription)
- **Calendrier** : Google Calendar API (OAuth2 refresh token)
- **Autres** : pandas, pytz, python-dateutil, requests

## Prérequis

- Python 3.11+
- Compte Supabase (projet créé)
- Compte Twilio avec SID, Auth Token et numéro
- Compte Google Cloud avec OAuth2 credentials (`client_secrets.json`)
- Clés API Deepgram (optionnel pour transcription)

## Installation rapide (local)

1. Clone le dépôt

```bash
git clone https://github.com/ton-utilisateur/telnek-config.git
cd telnek-config