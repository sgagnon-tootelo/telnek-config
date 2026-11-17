# Telnek AI – Web configuration interface

Streamlit admin interface for Telnek AI virtual receptionists (Amélie and other voices).

Sign-in is required. Access depends on the role: an admin sees every client, and a client user sees only their own company.

The app configures client profiles, call history, recordings, statistics, and Google Calendar. Authentication uses Supabase Auth.

The phone agent itself is [GrokVoiceAgent](https://github.com/sgagnon-tootelo/GrokVoiceAgent). Calls arrive over Twilio SIP into a LiveKit room and are handled by Grok Voice Realtime. This repository stores the configuration that agent reads. Saving a change here does not deploy the agent. Phone behavior goes to production with `lk agent deploy` in GrokVoiceAgent.

![Interface screenshot](https://via.placeholder.com/1200x600.png?text=Telnek+AI+Dashboard+screenshot)  
*(Replace this with a real screenshot.)*

## Features

- **Authentication and roles**:
  - Sign-in with Supabase Auth (email and password)
  - **Admin**: every client, the global dashboard, and cross-client statistics
  - **Client**: one company only, with a shorter set of tabs
- **Multi-client management**: pick and configure each company, within the role's scope
- **Agent settings**:
  - Company name, address, and opening hours, including a different range for each weekday
  - Specific instructions
  - Agent voice (native Grok Realtime, xAI custom voices, or ElevenLabs)
  - Transfer mode (blind, warm, or none) and the related phone numbers
  - Contacts, including a flag to transfer only while the office is open
- **Google Calendar** (OAuth2) for automatic booking when that client has a connected calendar
- **Call history**:
  - Filterable table
  - Transcript preview and WAV playback through a Twilio proxy
  - CSV download
- **Statistics**:
  - Total calls, completed calls, booked appointments, booking rate, average duration
  - Abandoned calls and abandonment rate
  - Booked appointments highlighted
  - Global views are limited to admins

## Stack

- **Frontend**: Streamlit
- **Backend**: Supabase (PostgreSQL, Auth, and Storage)
- **Calls and voice**: Twilio recordings, LiveKit, and Deepgram transcription
- **Calendar**: Google Calendar API (OAuth2 refresh token)
- **Other**: pandas, pytz, python-dateutil, requests

## Requirements

- Python 3.11+
- A Supabase project with Auth enabled
- Users in Supabase Auth and a configured `profiles` table (see below)
- A Twilio account with an account SID, an auth token, and a phone number
- A Google Cloud OAuth2 client (`client_secrets.json`)
- A Deepgram API key, optional, for transcription

## Local setup

1. Clone the repository

```bash
git clone https://github.com/sgagnon-tootelo/telnek-config.git
cd telnek-config
```

2. Create the secrets file

```bash
mkdir -p .streamlit
```

Create `.streamlit/secrets.toml` with at least:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Required to play call recordings
TWILIO_ACCOUNT_SID = "AC..."
TWILIO_AUTH_TOKEN = "..."
```

3. Configure authentication (the `profiles` table)

Run this in the Supabase SQL editor:

```sql
-- 1. Create the table once
create table if not exists profiles (
  id uuid references auth.users on delete cascade primary key,
  email text unique not null,
  role text not null check (role in ('admin','client')),
  client_id text,
  created_at timestamptz default now()
);

-- 2. Look up user ids: SELECT id, email FROM auth.users;
--    Look up a client: SELECT id, company_name FROM clients;

insert into profiles (id, email, role, client_id)
values
  ('<ADMIN-UUID>', 'admin@example.com', 'admin', null),
  ('<CLIENT-UUID>', 'client@example.com', 'client', '<client_id>')
on conflict (id) do update set role = excluded.role, client_id = excluded.client_id;
```

4. Start the app

```bash
streamlit run streamlit_app.py
```

Open http://localhost:8501. The app sends you to the sign-in page.

## Authentication

The app uses Supabase Auth and a `profiles` table for roles.

- An **admin** sees the whole interface, including the global dashboard.
- A **client** sees only their own company. The client is selected for them, and the tabs are limited to Configuration, History, and Statistics.

For local testing without a password, set this in `secrets.toml`:

```toml
DEV_BYPASS_AUTH = true
# DEV_BYPASS_ROLE = "client"
# DEV_BYPASS_CLIENT_ID = "the-real-id"
```

Leave this off in production.

## Usage

1. Sign in with a Supabase Auth account.
2. What you see depends on the role:
   - **Admin**: any client, plus the global dashboard and cross-client statistics.
   - **Client**: your company only. The global dashboard is hidden.
3. Voice, transfer, Google Calendar, and call playback follow the permissions of that role.

## Development

- `DEV_BYPASS_AUTH` signs you in automatically while you work locally.
- Which clients and global queries are visible is decided in the app from the `profiles` row.
- For real use, create the users in Supabase Authentication and link them in `profiles` with the right role and `client_id`.
