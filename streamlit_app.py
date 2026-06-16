import streamlit as st
import json
import pandas as pd
from pathlib import Path
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
from streamlit_autorefresh import st_autorefresh
import plotly.express as px

from i18n import (
    PRIMARY_LANGUAGES,
    TIMEZONE_OPTIONS,
    get_ui_lang,
    normalize_primary_language,
    primary_language_label,
    resolve_client_timezone,
    t,
    timezone_label,
)


def _t(key: str, **kwargs) -> str:
    return t(key, st.session_state, **kwargs)


APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "telnek_logo.png"


def render_app_header() -> None:
    col_logo, col_title = st.columns([1, 5], vertical_alignment="center")
    with col_logo:
        st.image(str(LOGO_PATH), width=240)
    with col_title:
        st.markdown(f"## {_t('app_subtitle')}")


def render_app_footer() -> None:
    st.divider()
    st.markdown(
        f'<p style="text-align:center;color:#888;font-size:0.85rem;margin:1rem 0;">'
        f'{_t("copyright_footer")}</p>',
        unsafe_allow_html=True,
    )


def stop_app() -> None:
    render_app_footer()
    st.stop()

# ==================== CONNEXION SUPABASE (avec gestion d'erreur conviviale) ====================
def init_supabase():
    """Initialise le client Supabase avec un message d'erreur clair si les secrets manquent."""
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        return create_client(supabase_url, supabase_key)
    except Exception:
        st.error("❌ **Fichier de secrets Streamlit manquant ou incomplet**", icon="🔐")

        st.markdown(r"""
        L'application n'a pas pu lire les variables de configuration (`SUPABASE_URL`, etc.).

        **Emplacements valides pour le fichier `secrets.toml` :**
        1. **Recommandé (projet)** :  
           `C:\chemin\vers\votre\projet\.streamlit\secrets.toml`
        2. **Global (utilisateur)** :  
           `C:\Users\VotreNom\.streamlit\secrets.toml`
        """)

        st.subheader("Étapes pour corriger :")

        st.markdown(r"""
        1. Dans l'explorateur de fichiers, allez dans le dossier du projet.

        2. Créez un **nouveau dossier** nommé exactement `.streamlit` (le point est important).

        3. À l'intérieur de ce dossier `.streamlit`, créez un fichier texte nommé `secrets.toml`.

        4. Collez dedans au minimum ceci (remplacez par vos vraies valeurs) :
        """)

        st.code("""SUPABASE_URL = "https://ton-projet.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Obligatoire pour la lecture des enregistrements audio dans l'onglet Historique
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token_ici"
""", language="toml")

        st.info("""
        **Pour tester rapidement sans les vrais comptes :**
        Ajoutez dans `.streamlit/secrets.toml` :

        DEV_BYPASS_AUTH = true
        # Pour simuler un client restreint :
        # DEV_BYPASS_ROLE = "client"
        # DEV_BYPASS_CLIENT_ID = "un-vrai-client-id"

        Laissez désactivé en utilisation normale.
        """)

        stop_app()

supabase: Client = init_supabase()

# ==================== AUTHENTIFICATION MULTI-UTILISATEUR (Supabase Auth + table profiles) ====================
#
# Table "profiles" (obligatoire) :
#   id uuid primary key references auth.users
#   email text
#   role text ('admin' | 'client')
#   client_id text (NULL pour admin, ou l'id exact d'un client pour les utilisateurs restreints)
#
# Règles appliquées :
#   - role = 'admin'  → accès complet (tous les clients + dashboard global)
#   - role = 'client' → accès restreint à son seul client_id
#
# La table profiles a été créée et remplie avec :
#   - sylvaing@videotron.ca (admin)
#   - telnekdev@gmail.com (client avec son client_id)
#
# Mode développement rapide (optionnel) :
#   Tu peux toujours activer le bypass dans secrets.toml avec :
#     DEV_BYPASS_AUTH = true
#     DEV_BYPASS_ROLE = "client"          # ou "admin"
#     DEV_BYPASS_CLIENT_ID = "..."        # (uniquement si role=client)
#
# Pour la production / usage normal : laisse le bypass désactivé.

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "fr"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_role = None
    st.session_state.user_client_id = None
    st.session_state.profile = None

def get_user_profile(email: str):
    """Récupère le profil depuis la table 'profiles' par email.
    Si la table n'existe pas ou le profil est absent, on retourne None (l'appelant gère l'erreur).
    """
    if not email:
        return None
    try:
        resp = supabase.table('profiles').select('*').eq('email', email.lower().strip()).limit(1).execute()
        if resp.data:
            return resp.data[0]
    except Exception as e:
        # Table probablement absente ou problème RLS / permissions
        print(f"[profiles] Erreur fetch profile pour {email}: {e}")
        # On laisse l'appelant afficher un message utile
    return None

def login_user(email: str, password: str):
    """Connexion via Supabase Auth + chargement du profil + rôle."""
    try:
        auth_resp = supabase.auth.sign_in_with_password({
            "email": email.strip(),
            "password": password
        })
        if not auth_resp or not auth_resp.user:
            st.error(_t("auth_failed"))
            return False

        profile = get_user_profile(email)
        if not profile:
            st.error(_t("no_profile", email=email))

            supabase.auth.sign_out()
            return False

        role = (profile.get('role') or 'client').lower()
        if role not in ('admin', 'client'):
            role = 'client'

        st.session_state.authenticated = True
        st.session_state.user_email = profile.get('email') or email
        st.session_state.profile = profile
        st.session_state.user_role = role
        st.session_state.user_client_id = profile.get('client_id')

        st.success(_t("connected_as", email=st.session_state.user_email, role=role))
        st.rerun()
        return True

    except Exception as e:
        st.error(_t("login_error", error=str(e)))
        return False

def logout_user():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    # Nettoyage complet de la session
    keys_to_clear = ["authenticated", "user_email", "user_role", "user_client_id", "profile",
                     "main_client_selector"]  # on nettoie aussi la clé du selectbox pour éviter les résidus
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

    st.rerun()

def get_clients():
    """Clients accessibles selon le rôle de l'utilisateur connecté."""
    role = st.session_state.get("user_role")
    if role == "admin":
        return supabase.table('clients').select('*').execute().data or []
    else:
        cid = st.session_state.get("user_client_id")
        if cid:
            return supabase.table('clients').select('*').eq('id', cid).execute().data or []
        return []

def update_client(client_id, data):
    return supabase.table('clients').update(data).eq('id', client_id).execute()

# ==================== INTERFACE ====================
st.set_page_config(page_title=_t("page_title"), page_icon=str(LOGO_PATH), layout="wide")
render_app_header()

# ==================== GATE D'AUTHENTIFICATION ====================
if not st.session_state.get("authenticated", False):

    # === MODE DÉVELOPPEMENT (optionnel) ===
    # Active un login automatique sans mot de passe (très pratique pour tester).
    # Ajoute dans .streamlit/secrets.toml :
    #
    #   DEV_BYPASS_AUTH = true
    #   # Pour simuler un utilisateur client :
    #   # DEV_BYPASS_ROLE = "client"
    #   # DEV_BYPASS_CLIENT_ID = "le-vrai-id-d-un-client"
    #
    # Laisse désactivé pour l'utilisation normale avec les vrais comptes Supabase Auth.
    if st.secrets.get("DEV_BYPASS_AUTH", False):
        # Permet de tester facilement les deux rôles sans table profiles
        bypass_role = str(st.secrets.get("DEV_BYPASS_ROLE", "admin")).lower()
        bypass_client_id = st.secrets.get("DEV_BYPASS_CLIENT_ID", None)

        if bypass_role not in ("admin", "client"):
            bypass_role = "admin"

        st.session_state.authenticated = True
        st.session_state.user_email = f"dev-{bypass_role}@local.test"
        st.session_state.user_role = bypass_role
        st.session_state.user_client_id = bypass_client_id if bypass_role == "client" else None
        st.session_state.profile = {"role": bypass_role, "email": st.session_state.user_email}

        if bypass_role == "admin":
            st.info(_t("dev_admin"))
        else:
            st.info(_t("dev_client", client_id=bypass_client_id))

        st.rerun()

    lang_col, _ = st.columns([1, 3])
    with lang_col:
        st.selectbox(
            _t("ui_language"),
            options=["fr", "en"],
            format_func=lambda x: "Français" if x == "fr" else "English",
            key="ui_lang",
        )

    st.subheader(_t("login_required"))
    st.caption(_t("login_caption"))

    with st.form(key="login_form", clear_on_submit=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            default_email = "sylvaing@videotron.ca"
            email = st.text_input(_t("email"), value=default_email, placeholder="votre@email.com")
        with col2:
            password = st.text_input(_t("password"), type="password", placeholder="••••••••")

        submitted = st.form_submit_button(_t("login_btn"), type="primary", use_container_width=True)

        if submitted:
            login_user(email, password)

    st.info(_t("login_info"))
    stop_app()

# ==================== SIDEBAR UTILISATEUR + DÉCONNEXION ====================
with st.sidebar:
    st.selectbox(
        _t("ui_language"),
        options=["fr", "en"],
        format_func=lambda x: "Français" if x == "fr" else "English",
        key="ui_lang",
    )
    st.divider()
    st.markdown(f"### {_t('session')}")
    st.markdown(f"**{st.session_state.get('user_email', '—')}**")
    role = st.session_state.get('user_role', '—')
    role_emoji = "🛡️" if role == "admin" else "👤"
    st.markdown(f"{_t('role')} : {role_emoji} **{role}**")

    if st.session_state.get("user_client_id"):
        st.caption(f"{_t('restricted_client')} : `{st.session_state['user_client_id']}`")

    st.divider()
    if st.button(_t("logout"), type="secondary", use_container_width=True):
        logout_user()

# ==================== SÉLECTION DU CLIENT (RÔLE-AWARE) ====================
clients = get_clients()

if not clients:
    st.error(_t("no_clients"))
    stop_app()

is_admin = (st.session_state.get("user_role") == "admin")

# Tri stable par ID
clients_sorted = sorted(clients, key=lambda c: c.get('id', '').lower())
client_ids = [c['id'] for c in clients_sorted if c.get('id')]

if is_admin:
    # Comportement original pour les admins : choix libre parmi tous les clients
    # Utilise la session_state gérée par la key du widget (plus robuste que locals())
    prev_value = st.session_state.get("main_client_selector")
    default_index = client_ids.index(prev_value) if prev_value in client_ids else 0
    selected_client_id = st.selectbox(
        _t("select_client"),
        options=client_ids,
        key="main_client_selector",
        index=default_index
    )
else:
    # Utilisateur client : un seul client possible → auto-sélection + affichage clair
    selected_client_id = client_ids[0] if client_ids else None
    if selected_client_id:
        company_name = next((c.get('company_name', selected_client_id) for c in clients if c['id'] == selected_client_id), selected_client_id)
        st.success(f"{_t('restricted_access')} : **{company_name}** (`{selected_client_id}`)")

if selected_client_id:
    client = next((c for c in clients if c['id'] == selected_client_id), None)
    if client is None:
        st.error(_t("client_not_found"))
        stop_app()

    client_tz = pytz.timezone(resolve_client_timezone(client))

    # ====================== TABS PRINCIPAUX (conditionnels selon rôle) ======================
    if is_admin:
        tab_list = [
            _t("tab_global"),
            _t("tab_config"),
            _t("tab_calls"),
            _t("tab_stats"),
        ]
        tabs = st.tabs(tab_list)
        tab_global = tabs[0]
        tab_config = tabs[1]
        tab_appels = tabs[2]
        tab_stats = tabs[3]
    else:
        tab_list = [
            _t("tab_config"),
            _t("tab_calls"),
            _t("tab_stats"),
        ]
        tabs = st.tabs(tab_list)
        tab_config = tabs[0]
        tab_appels = tabs[1]
        tab_stats = tabs[2]

    # ====================== CONTENU DES ONGLETS (chaque with doit contenir TOUT ce qui va dedans) ======================

    if is_admin:
        with tab_global:
            st.subheader(_t("global_dashboard"))
            
            auto_refresh = st.toggle(_t("auto_refresh"), 
                                    value=True, key="global_refresh_top")
        
            if auto_refresh:
                st_autorefresh(interval=5000, limit=300, key="global_auto_top_level")

            # ====================== APPELS EN COURS (live) ======================
            live_response = supabase.table('vw_appels_clients') \
                .select('client_id, company_name, call_date, call_time, caller_number, room_name, status_label, started_at') \
                .eq('status', 'in_progress') \
                .gte('started_at', (datetime.now(pytz.utc) - timedelta(minutes=90)).isoformat()) \
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
                    lambda x: _t("duration_live", duration=str(now - x).split('.')[0])
                    if (now - x).total_seconds() > 60 else _t("less_than_minute")
                )
                
                display_cols = ['company_name', 'call_date', 'call_time', 'caller_number', 'Durée en cours', 'room_name']
                styled = df_global[display_cols].style.apply(
                    lambda row: ['background-color: #d4edda'] * len(row) if 'min' in str(row['Durée en cours']) else [''] * len(row),
                    axis=1
                )
                
                st.dataframe(styled, use_container_width=True, hide_index=True)
                st.metric(_t("live_calls_total"), len(df_global))
            else:
                st.success(_t("live_calls_none"))

            st.divider()
            st.subheader(_t("last_call_global"))

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
                    label=_t("last_call_metric"),
                    value=formatted_time,
                    delta=f"{last.get('company_name', 'Inconnu')} • {last.get('caller_number', 'N/A')}"
                )
                st.caption(f"**{_t('status')} :** {last.get('status_label', '—')}")
            else:
                st.info(_t("no_calls_yet"))
            
            st.divider()
            st.subheader(_t("cumulative_stats"))

            stats_response = supabase.table('vw_stats_appels_clients').select('*').execute()
        
            if stats_response.data:
                df_stats = pd.DataFrame(stats_response.data)
                
                # Récupère les noms d'entreprise
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
                with col1: st.metric(_t("metric_total"), total_appels)
                with col2: st.metric(_t("metric_completed"), completes)
                with col3: st.metric(_t("metric_appointments"), rdv_reserves)
                with col4: st.metric(_t("metric_avg_duration"), f"{duree_moyenne} s")
                with col5: st.metric(_t("metric_abandoned"), appels_abandonnes)
                with col6: st.metric(_t("metric_confirmed"), rdv_confirmes)
                with col7: st.metric(_t("metric_cancelled"), rdv_annules)

                # Tableau récap par client + ligne TOTAL
                df_stats_display = df_stats[['company_name', 'total_appels', 'appels_completes', 'rdv_reserves', 'duree_moyenne_sec']].copy()
                df_stats_display = df_stats_display.rename(columns={
                    'company_name': _t("col_client"),
                    'total_appels': _t("col_total"),
                    'appels_completes': _t("col_completed"),
                    'rdv_reserves': _t("col_appointments"),
                    'duree_moyenne_sec': _t("col_avg_sec"),
                })
                df_stats_display.loc[len(df_stats_display)] = [
                    _t("col_total_row"), total_appels, completes, rdv_reserves, duree_moyenne
                ]
                
                st.dataframe(df_stats_display.style.set_properties(subset=['Client'], **{'font-weight': 'bold'}), 
                            use_container_width=True, hide_index=True)
            else:
                st.info(_t("no_stats"))

    with tab_config:
        st.subheader(_t("config_for", client_id=selected_client_id))
        
        # ====================== HELPER ROBUSTE POUR JSON ======================
        def safe_json_loads(data):
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except:
                    return {}
            return data or {}
        
        def safe_json_dumps(data):
            data = safe_json_loads(data)
            return json.dumps(data, indent=4, ensure_ascii=False)
        
        ui_lang = get_ui_lang(st.session_state)
        st.subheader(_t("locale_section"))
        col_lang, col_tz = st.columns(2)
        current_lang = normalize_primary_language(client.get("primary_language"))
        lang_options = [o["value"] for o in PRIMARY_LANGUAGES]
        with col_lang:
            primary_language_selected = st.selectbox(
                _t("primary_language"),
                options=lang_options,
                format_func=lambda v: primary_language_label(v, ui_lang),
                index=lang_options.index(current_lang) if current_lang in lang_options else 0,
            )
        current_tz = resolve_client_timezone(client)
        tz_options = [o["iana"] for o in TIMEZONE_OPTIONS]
        if current_tz not in tz_options:
            tz_options = [current_tz] + tz_options
        with col_tz:
            timezone_selected = st.selectbox(
                _t("timezone"),
                options=tz_options,
                format_func=lambda v: timezone_label(v, ui_lang),
                index=tz_options.index(current_tz) if current_tz in tz_options else 0,
            )
        st.caption(
            _t("locale_hint_en") if primary_language_selected == "en-US" else _t("locale_hint_fr")
        )

        company_name = st.text_input(_t("company_name"), value=client.get('company_name', ''))
        company_address = st.text_input(_t("company_address"), value=client.get('company_address', ''))
        company_hours = st.text_input(_t("company_hours"), value=client.get('company_hours', ''))
        
        col1, col2 = st.columns(2)
        with col1:
            opening_hour = st.number_input(_t("opening_hour"), 
                                         value=client.get('opening_hour', 9), min_value=0, max_value=23, step=1)
        with col2:
            closing_hour = st.number_input(_t("closing_hour"), 
                                         value=client.get('closing_hour', 17), min_value=0, max_value=24, step=1)
    
        st.subheader(_t("sms_numbers"))
        st.caption(_t("sms_caption"))
    
        # Chargement de la liste actuelle
        admin_phones_raw = client.get('admin_phones')
        if isinstance(admin_phones_raw, list):
            current_phones = "\n".join(str(p).strip() for p in admin_phones_raw if str(p).strip())
        elif isinstance(admin_phones_raw, str) and admin_phones_raw.strip():
            current_phones = admin_phones_raw
        else:
            current_phones = client.get('admin_phone', '')  # fallback temporaire sur l’ancienne colonne
    
        admin_phones_edited = st.text_area(
            _t("sms_phones"),
            value=current_phones,
            height=120,
            help="Exemple :\n+15149474976\n+15145551234"
        )
        
        callee_number = st.text_input(_t("virtual_number"), value=client.get('callee_number', ''), disabled=True)
        
        instructions_specific = st.text_area(_t("instructions"), 
                                           value=client.get('instructions_specific', ''), height=120)
        
        base_url = st.text_input(_t("website"), value=client.get('base_url', ''))
        
        # ====================== URL_MAP (protégé) ======================
        url_map_str = safe_json_dumps(client.get('url_map', {}))
        url_map_edited = st.text_area(_t("url_map"), 
                                      value=url_map_str, height=150)
        
        if st.button(_t("validate_json")):
            try:
                json.loads(url_map_edited)
                st.success(_t("json_valid"))
                st.json(json.loads(url_map_edited))
            except json.JSONDecodeError as e:
                st.error(_t("json_invalid", error=e))
    
        default_agent = "Emily" if primary_language_selected == "en-US" else "Amélie"
        agent_name = st.text_input(
            _t("agent_name"),
            value=client.get('agent_name') or default_agent,
        )
        
        st.subheader(_t("voice_section"))
    
        # Chargement dynamique des voix depuis Supabase
        voices_response = supabase.table('voices') \
            .select('*') \
            .eq('is_active', True) \
            .order('sort_order') \
            .execute()
    
        all_voices = voices_response.data or []
    
        grok_voices = [v for v in all_voices if v['provider'] == 'grok']
        eleven_voices = [v for v in all_voices if v['provider'] == 'elevenlabs']
    
        tts_provider_options = [
            {"value": "xai", "label": _t("tts_xai")},
            {"value": "elevenlabs", "label": _t("tts_eleven")},
        ]
    
        current_tts = client.get('tts_provider', 'xai')
        default_tts_index = next((i for i, opt in enumerate(tts_provider_options) if opt["value"] == current_tts), 0)
    
        selected_tts = st.selectbox(_t("tts_provider"), options=tts_provider_options,
                                    format_func=lambda x: x["label"], index=default_tts_index)
        tts_provider_selected = selected_tts["value"]
    
        # === GROK ===
        if tts_provider_selected == "xai":
            st.caption(_t("grok_caption"))
    
            voice_options = [{"value": v['voice_key'], "label": v['display_label']} for v in grok_voices]
            default_voice = "eve" if primary_language_selected == "en-US" else "ara"
            current_voice_key = client.get('voice_name') or default_voice
            default_voice_index = next((i for i, opt in enumerate(voice_options) if opt["value"] == current_voice_key), 0)
    
            selected_voice = st.selectbox(_t("grok_standard"), options=voice_options,
                                          format_func=lambda x: x["label"], index=default_voice_index)
    
            grok_custom_raw = st.text_input(
                _t("grok_custom"),
                value=client.get('grok_custom_voice_id', '') or "",
                placeholder="ex: custom_abc123...",
                help=_t("grok_custom_help"),
            )
            grok_custom_voice_id = grok_custom_raw.strip() if grok_custom_raw else ""
    
            # Priorité au custom
            if grok_custom_voice_id:
                voice_value = grok_custom_voice_id
                st.success(_t("grok_custom_active"))
            else:
                voice_value = selected_voice["value"]
    
        else:
            voice_options = [{"value": v['voice_key'], "label": v['display_label']} for v in eleven_voices]
            current_voice_key = client.get('elevenlabs_voice_id', voice_options[0]['value'] if voice_options else "")
            default_voice_index = next((i for i, opt in enumerate(voice_options) if opt["value"] == current_voice_key), 0)
    
            selected_voice = st.selectbox(_t("eleven_voice"), options=voice_options,
                                          format_func=lambda x: x["label"], index=default_voice_index)
            voice_value = selected_voice["value"]
            grok_custom_voice_id = ""
    
        st.subheader(_t("transfer_section"))
        transfer_mode_options = [
            {"value": "blind", "label": _t("transfer_blind")},
            {"value": "warm",  "label": _t("transfer_warm")},
            {"value": "none",  "label": _t("transfer_none")},
        ]
        current_mode = client.get('transfer_mode', 'none')
        default_mode_index = next((i for i, opt in enumerate(transfer_mode_options) if opt["value"] == current_mode), 2)
        selected_mode = st.selectbox(_t("transfer_section"), options=transfer_mode_options, 
                                     format_func=lambda x: x["label"], index=default_mode_index)
        transfer_mode_selected = selected_mode["value"]
    
        # ====================== NUMÉROS DE TRANSFERT (protégé) ======================
        transfer_numbers_str = ""
        if transfer_mode_selected != "none":
            transfer_numbers_str = safe_json_dumps(client.get('transfer_numbers', {}))
            transfer_numbers_edited = st.text_area(_t("transfer_numbers"), 
                                                 value=transfer_numbers_str, height=150)
            
            if st.button(_t("validate_transfer_json")):
                try:
                    json.loads(transfer_numbers_edited)
                    st.success(_t("json_valid"))
                    st.json(json.loads(transfer_numbers_edited))
                except json.JSONDecodeError as e:
                    st.error(_t("json_invalid", error=e))
        else:
            transfer_numbers_edited = "{}"  # pour le save
    
        # Toggles
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            get_caller_history_flag = st.toggle(
                _t("toggle_memory"), 
                value=client.get('get_caller_history_flag', False)
            )
        with col2:
            call_transcription_flag = st.toggle(
                _t("toggle_transcription"), 
                value=client.get('call_transcription_flag', False)
            )
        with col3:
            confirmation_required = st.toggle(
                _t("toggle_confirmation"),
                value=client.get('confirmation_required', True)
            )
        with col4:
            hangup_message_flag = st.toggle(
                _t("toggle_hangup_sms"),
                value=client.get('hangup_message_flag', False)
            )
    
        st.subheader(_t("google_section"))
        fresh_client = next((c for c in get_clients() if c['id'] == selected_client_id), client)
        current_token = fresh_client.get('google_refresh_token')
        has_google = bool(current_token)
    
        col_connect, col_disconnect = st.columns([3, 2])
        with col_connect:
            if has_google:
                st.success(_t("google_connected"))
            else:
                if st.button(_t("google_connect"), type="primary"):
                    SCOPES = ['https://www.googleapis.com/auth/calendar']
                    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", scopes=SCOPES)
                    credentials = flow.run_local_server(port=8502, prompt='consent')
                    if credentials and credentials.refresh_token:
                        supabase.table("clients").update({"google_refresh_token": credentials.refresh_token}).eq("id", selected_client_id).execute()
                        st.success(_t("google_connected_ok"))
                        st.rerun()
                    else:
                        st.error(_t("google_no_token"))
    
        with col_disconnect:
            if has_google:
                if st.button(_t("google_disconnect"), type="secondary"):
                    supabase.table("clients").update({"google_refresh_token": None}).eq("id", selected_client_id).execute()
                    st.success(_t("google_removed"))
                    st.rerun()
    
        if st.button(_t("save_config"), type="primary"):
            try:
                url_map_parsed = json.loads(url_map_edited) if url_map_edited.strip() else {}
            except:
                st.error(_t("url_map_invalid"))
                stop_app()
    
            transfer_numbers_parsed = {}
            if transfer_mode_selected != "none":
                try:
                    transfer_numbers_parsed = json.loads(transfer_numbers_edited) if transfer_numbers_edited.strip() else {}
                except:
                    st.error(_t("transfer_json_invalid"))
                    stop_app()
            else:
                transfer_numbers_parsed = client.get('transfer_numbers', {}) or {}
    
            # === CONVERSION TEXTE → LISTE pour admin_phones ===
            admin_phones_list = [
                num.strip() for num in admin_phones_edited.splitlines()
                if num.strip()
            ]
    
            updated_data = {
                'primary_language': primary_language_selected,
                'timezone': timezone_selected,
                'company_name': company_name,
                'company_address': company_address,
                'company_hours': company_hours,
                'opening_hour': opening_hour,
                'closing_hour': closing_hour,
                'admin_phones': admin_phones_list,
                'instructions_specific': instructions_specific,
                'base_url': base_url,
                'url_map': url_map_parsed,
                'agent_name': agent_name,
                'tts_provider': tts_provider_selected,
                'voice_name': voice_value if tts_provider_selected == "xai" else client.get('voice_name', 'ara'),
                'elevenlabs_voice_id': voice_value if tts_provider_selected == "elevenlabs" else None,
                'grok_custom_voice_id': grok_custom_voice_id if tts_provider_selected == "xai" else None,
                'transfer_mode': transfer_mode_selected,
                'transfer_numbers': transfer_numbers_parsed,
                'get_caller_history_flag': get_caller_history_flag,
                'call_transcription_flag': call_transcription_flag,
                'confirmation_required': confirmation_required,
                'hangup_message_flag': hangup_message_flag
            }
            update_client(selected_client_id, updated_data)
            st.success(_t("save_ok"))
            st.rerun()
    
    # ====================== TAB HISTORIQUE DES APPELS + ÉCOUTE WAV (MIS À JOUR) ======================
    with tab_appels:
        st.subheader(_t("calls_history", client_id=selected_client_id))
        
        appels_response = supabase.table('vw_appels_clients') \
            .select('*') \
            .eq('client_id', selected_client_id) \
            .order('started_at', desc=True) \
            .limit(500) \
            .execute()
        
        if appels_response.data:
            df = pd.DataFrame(appels_response.data)
            
            for col in ['started_at', 'appointment_start']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    mask = df[col].notna()
                    if mask.any():
                        if df.loc[mask, col].dt.tz is None:
                            df.loc[mask, col] = df.loc[mask, col].dt.tz_localize('UTC')
                        df.loc[mask, col] = df.loc[mask, col].dt.tz_convert(client_tz)
                                    
            # ====================== NOUVELLE COLONNE "ISSUE / ACTION" ======================
            def get_issue_label(row):
                if row.get('appointment_booked'):
                    return _t("issue_appointment")
                elif row.get('message_taken'):
                    return _t("issue_message")
                elif row.get('transfer_success'):
                    return _t("issue_transfer")
                elif row.get('status') == 'abandoned':
                    return _t("issue_abandoned")
                else:
                    return _t("issue_done")

            df[_t("result_action")] = df.apply(get_issue_label, axis=1)

            def get_detail(row):
                if row.get('message_taken'):
                    reason = str(row.get('message_reason') or "")
                    return reason[:70] + "..." if len(reason) > 70 else reason
                elif row.get('transfer_success'):
                    dept = str(row.get('transfer_department') or "")
                    number = str(row.get('transfer_to_number') or "")
                    if dept and number:
                        return f"{dept} ({number})"
                    return dept or number
                else:
                    return "—"

            df[_t("detail")] = df.apply(get_detail, axis=1)

            def color_issue(val):
                val_str = str(val)
                if "📅" in val_str:
                    return 'background-color: #d4edda; color: #155724; font-weight: bold'
                elif "📩" in val_str:
                    return 'background-color: #cce5ff; color: #004085; font-weight: bold'
                elif "🔄" in val_str:
                    return 'background-color: #fff3cd; color: #856404; font-weight: bold'
                elif "❌" in val_str:
                    return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                else:
                    return 'background-color: #e2e3e5; color: #383d41'

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
                '🎧', 'status_label', _t("result_action"), _t("detail"),
                'appointment_start', 'appointment_name', 'duration_formatted',
                'transcript_preview'
            ]
            available_cols = [col for col in display_columns if col in df.columns]
            
            def highlight_rdv(row):
                if row.get('appointment_booked'):
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)
            
            styled_df = df[available_cols].style.apply(highlight_rdv, axis=1)
            styled_df = styled_df.map(color_issue, subset=[_t("result_action")])
            
            st.caption(_t("calls_click_hint"))
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
            st.download_button(_t("download_csv"), csv, 
                             f"appels_{selected_client_id}.csv", "text/csv")

            # ====================== DÉTAIL SÉLECTIONNÉ ======================
            if event.selection.rows:
                row = df.iloc[event.selection.rows[0]]
                
                st.divider()
                st.subheader(_t("call_detail", date=row.get('call_date'), time=row.get('call_time'), caller=row.get('caller_number')))
                
                st.markdown(f"**{_t('appointment_status')} :** {row.get('statut_rdv', '—')}")

                st.subheader(_t("recording"))
                recording_url = row.get('recording_url')
                if recording_url and isinstance(recording_url, str) and recording_url.startswith('http'):
                    try:
                        account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
                        auth_token = st.secrets["TWILIO_AUTH_TOKEN"]
                        response = requests.get(recording_url, auth=(account_sid, auth_token), timeout=15)
                        if response.status_code == 200:
                            audio_bytes = response.content
                            st.success(_t("recording_ok"))
                            st.audio(audio_bytes, format="audio/wav")
                            st.download_button(
                                label=_t("download_wav"),
                                data=audio_bytes,
                                file_name=f"appel_{row.get('caller_number','inconnu')}_{row.get('call_date','')}.wav",
                                mime="audio/wav"
                            )
                        else:
                            st.error(_t("recording_denied", code=response.status_code))
                    except Exception as e:
                        st.error(_t("recording_error", error=str(e)))
                else:
                    st.info(_t("no_recording"))
                
                st.subheader(_t("transcript_full"))
                transcript = row.get('transcript', '')
                if transcript and str(transcript).strip():
                    st.text_area(_t("transcript_full"), transcript, height=380)
                else:
                    st.info(_t("no_transcript"))
            else:
                st.info(_t("select_row"))
                
        else:
            st.info(_t("no_calls_yet"))

    # ====================== TAB STATISTIQUES – VERSION FINALE ULTRA-ROBUSTE ======================
    with tab_stats:
        st.subheader(_t("stats_for", client_id=selected_client_id))
        
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
    
            # ====================== TRANSFERTS & MESSAGES ======================
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
    
            # Métriques principales
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
            with col1: st.metric(_t("metric_total"), total)
            with col2: st.metric(_t("metric_completed"), completes)
            with col3: st.metric(_t("metric_appointments"), booked, delta=f"{pourcent_rdv:.1f}%")
            with col4: st.metric(_t("metric_confirmed_short"), confirmed)
            with col5: st.metric(_t("metric_cancelled_short"), cancelled)
            with col6: st.metric(_t("metric_abandoned"), appels_abandonnes, delta=f"{taux_abandon:.1f}%")
            with col7: st.metric(_t("metric_avg_duration"), f"{duree_moy:.1f} s")
            with col8: st.metric(_t("metric_confirm_rate"), f"{taux_confirmation:.1f}%")
    
            st.divider()
            colA, colB, colC, colD = st.columns(4)
            with colA: st.metric(_t("metric_transfers_tried"), transferred)
            with colB: st.metric(_t("metric_transfers_ok"), transferred_success, 
                                delta=f"{(transferred_success / transferred * 100) if transferred > 0 else 0:.1f}%")
            with colC: st.metric(_t("metric_messages"), messages_pris)
            with colD: st.metric(_t("metric_normal"), total - transferred - messages_pris)
    
            st.caption(_t("funnel", total=total, booked=booked, confirmed=confirmed, transferred=transferred, messages=messages_pris))
    
            st.divider()
            st.subheader(_t("charts"))
    
            col_g1, col_g2 = st.columns(2)
    
            # Pie chart (toujours OK)
            with col_g1:
                repartition = pd.DataFrame({
                    "Type": [_t("chart_pie_normal"), _t("chart_pie_transfer"), _t("chart_pie_message")],
                    "Nombre": [total - transferred - messages_pris, transferred, messages_pris]
                })
                fig_pie = px.pie(repartition, values="Nombre", names="Type",
                               title=_t("chart_pie_title"),
                               color_discrete_sequence=px.colors.sequential.Blues)
                st.plotly_chart(fig_pie, use_container_width=True)
    
            # Bar chart motifs – PROTECTION EN BÉTON (plus jamais d'erreur)
            with col_g2:
                if appels_response.data and 'appointment_reason' in df_detail.columns:
                    booked_reasons = df_detail[df_detail['appointment_booked'] == True]['appointment_reason'].dropna()
                    reasons = booked_reasons.value_counts().head(8)
                    
                    if len(reasons) > 0:
                        fig_bar = px.bar(
                            x=reasons.index.tolist(),
                            y=reasons.values.tolist(),
                            labels={"x": _t("chart_bar_x"), "y": _t("chart_bar_y")},
                            title=_t("chart_bar_title"),
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        st.info(_t("no_reasons"))
                else:
                    st.info(_t("no_reasons_client"))
    
            st.divider()
            st.subheader(_t("detail_table"))
            
            sort_option = st.selectbox(
                _t("sort_calls"),
                options=[_t("sort_newest"), _t("sort_oldest")],
                index=0,
                key=f"stats_sort_{selected_client_id}"
            )
            
            # Tri du dataframe (on travaille sur une copie pour ne pas affecter les calculs précédents)
            df_sorted = df_detail.copy()
            
            if not df_sorted.empty and 'started_at' in df_sorted.columns:
                df_sorted['started_at'] = pd.to_datetime(df_sorted['started_at'], errors='coerce')
                ascending = sort_option == _t("sort_oldest")
                df_sorted = df_sorted.sort_values(by='started_at', ascending=ascending).reset_index(drop=True)
            elif not df_sorted.empty:
                # Fallback si started_at n'existe pas
                df_sorted = df_sorted.sort_values(by=['call_date', 'call_time'], ascending=False)
            
            # Préparation du tableau d'affichage
            df_display = df_sorted[['call_date', 'call_time', 'caller_number', 'status',
                                   'transfer_attempted', 'transfer_success', 'message_taken',
                                   'appointment_booked', 'appointment_confirmed', 'appointment_cancelled',
                                   'appointment_reason']].copy()        
            def color_row(row):
                if row.get('appointment_confirmed', False):
                    return ['background-color: #d4edda'] * len(row)
                elif row.get('appointment_cancelled', False):
                    return ['background-color: #f8d7da'] * len(row)
                elif row.get('transfer_success', False) is True:
                    return ['background-color: #fff3cd'] * len(row)
                return [''] * len(row)
            
            styled = df_display.style.apply(color_row, axis=1)
            st.dataframe(styled, use_container_width=True, hide_index=True)
    
            # Export CSV
            csv = df_detail.to_csv(index=False).encode('utf-8')
            st.download_button(_t("download_all_csv"), csv, 
                             f"stats_detaillees_{selected_client_id}.csv", "text/csv")
        
        else:
            st.info(_t("no_stats_client"))

render_app_footer()