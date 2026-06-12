# Telnek AI – Interface de Configuration Web

Interface d'administration Streamlit pour gérer les agents virtuels de réception Telnek AI (Amélie et autres voix).

**Nouvelle fonctionnalité majeure :** Authentification multi-utilisateurs avec contrôle d'accès par rôle (admin / client restreint).

Permet de configurer facilement les profils clients, consulter l'historique des appels, écouter les enregistrements, voir les statistiques et connecter Google Calendar. L'accès est maintenant sécurisé par une page de connexion Supabase Auth.

![Capture d'écran de l'interface](https://via.placeholder.com/1200x600.png?text=Capture+d%27%C3%A9cran+Telnek+AI+Dashboard)  
*(Ajoute une vraie capture d'écran ici pour rendre le README plus attractif)*

## Fonctionnalités principales

- **Authentification et rôles** :
  - Connexion via Supabase Auth (email + mot de passe)
  - **Rôle Admin** : accès complet à tous les clients, dashboard global, statistiques croisées
  - **Rôle Client** : accès restreint à un seul client (son entreprise), interface simplifiée (3 onglets)
- **Gestion multi-clients** : sélection et configuration de chaque entreprise cliente (visible selon le rôle)
- **Paramètres de l'agent** :
  - Nom de l’entreprise, adresse, heures d’ouverture
  - Instructions spécifiques (personnalisation du comportement)
  - Voix de l’agent (Grok Realtime natif + Custom Voices xAI, ou ElevenLabs)
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
  - (Les vues globales sont réservées aux administrateurs)

## Technologies utilisées

- **Frontend** : Streamlit
- **Backend** : Supabase (PostgreSQL + Auth + Storage)
- **Appels & Voix** : Twilio (enregistrements) + LiveKit + Deepgram (transcription)
- **Calendrier** : Google Calendar API (OAuth2 refresh token)
- **Autres** : pandas, pytz, python-dateutil, requests

## Prérequis

- Python 3.11+
- Compte Supabase (projet créé avec Auth activé)
- Utilisateurs créés dans Supabase Auth + table `profiles` configurée (voir section ci-dessous)
- Compte Twilio avec SID, Auth Token et numéro
- Compte Google Cloud avec OAuth2 credentials (`client_secrets.json`)
- Clés API Deepgram (optionnel pour transcription)

## Installation rapide (local)

1. Clone le dépôt

```bash
git clone https://github.com/ton-utilisateur/telnek-config.git
cd telnek-config

2. Crée le fichier de secrets

```bash
mkdir -p .streamlit
```

Crée le fichier `.streamlit/secrets.toml` avec au minimum :

```toml
SUPABASE_URL = "https://ton-projet.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Pour l'écoute des enregistrements audio
TWILIO_ACCOUNT_SID = "AC..."
TWILIO_AUTH_TOKEN = "..."
```

3. Configure l'authentification (table `profiles`)

Exécute dans l'éditeur SQL Supabase :

```sql
-- 1. Crée la table (une seule fois)
create table if not exists profiles (
  id uuid references auth.users on delete cascade primary key,
  email text unique not null,
  role text not null check (role in ('admin','client')),
  client_id text,
  created_at timestamptz default now()
);

-- 2. Récupère les UUIDs : SELECT id, email FROM auth.users;
--    Récupère un client : SELECT id, company_name FROM clients;

insert into profiles (id, email, role, client_id)
values
  ('<UUID-ADMIN>', 'admin@exemple.com', 'admin', null),
  ('<UUID-CLIENT>', 'client@exemple.com', 'client', '<client_id>')
on conflict (id) do update set role = excluded.role, client_id = excluded.client_id;
```

4. Lance l'application

```bash
streamlit run streamlit_app.py
```

Ouvre ton navigateur sur http://localhost:8501. Tu seras redirigé vers la page de connexion.

## Configuration de l'authentification

L'application utilise Supabase Auth + une table `profiles` pour gérer les rôles.

- Un utilisateur **admin** voit l'intégralité de l'interface (dashboard global inclus).
- Un utilisateur **client** ne voit que son propre client (sélection automatique, onglets limités à Configuration / Historique / Statistiques).

Le mode développement rapide (pour tester sans mot de passe) peut être activé dans `secrets.toml` :

```toml
DEV_BYPASS_AUTH = true
# DEV_BYPASS_ROLE = "client"
# DEV_BYPASS_CLIENT_ID = "le-vrai-id"
```

Laisse ce mode désactivé en production / usage normal.

## Utilisation

1. Connecte-toi avec un compte Supabase Auth.
2. Selon ton rôle :
   - **Admin** : sélectionne n'importe quel client, accès complet au dashboard global et aux statistiques croisées.
   - **Client** : tu es automatiquement limité à ton entreprise. Le dashboard global n'apparaît pas.
3. Toutes les fonctionnalités (config voix Grok/ElevenLabs, transferts, Google Calendar, écoute des appels, etc.) sont disponibles selon les permissions de ton rôle.

## Développement

- Le mode `DEV_BYPASS_AUTH` est très pratique pendant le développement (login automatique).
- La logique de scoping (clients visibles + requêtes globales) est gérée côté application en fonction du profil chargé depuis la table `profiles`.
- Pour un usage réel, crée les utilisateurs dans Supabase Authentication et lie-les dans `profiles` avec le bon rôle et `client_id`.
