"""Telnek Console — auth shell and page routing."""

from __future__ import annotations

import base64
from pathlib import Path

import pytz
import streamlit as st
from supabase import Client, create_client

from app_context import AppContext
from i18n import normalize_ui_lang, resolve_client_timezone, t
from views.calls import render_calls_page
from views.config import render_config_page
from views.dashboard import render_dashboard_page
from views.stats import render_stats_page
from ui.components import app_header_html
from ui.metrics_display import (
    LATENCY_COST_RAW_COLUMNS,
    latency_cost_column_keys,
    strip_latency_cost_raw_columns as _strip_latency_cost_raw_columns,
)
from ui.nav import (
    ADMIN_NAV_PAGES,
    CLIENT_NAV_PAGES,
    NAV_PAGE_CALLS,
    NAV_PAGE_CONFIG,
    NAV_PAGE_GLOBAL,
    NAV_PAGE_STATS,
    default_nav_page,
    ensure_nav_page,
    nav_page_label,
    nav_pages_for_role,
)
from ui.session_panel import render_password_change_form
from ui.sidebar_state import normalize_client_selector
from ui.theme import inject_brand_css


def _t(key: str, **kwargs) -> str:
    return t(key, st.session_state, **kwargs)


APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "telnek_logo.png"


def _logo_data_uri() -> str:
    encoded = base64.standard_b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_brand_subtitle(*, variant: str = "login") -> None:
    subtitle = _t("app_subtitle")
    modifier = (
        "telnek-brand-subtitle--login"
        if variant == "login"
        else "telnek-brand-subtitle--app"
    )
    st.markdown(
        f'<div class="telnek-brand-subtitle {modifier}">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def render_app_header() -> None:
    st.markdown(
        app_header_html(subtitle=_t("app_subtitle"), logo_data_uri=_logo_data_uri()),
        unsafe_allow_html=True,
    )


def render_login_page() -> None:
    normalize_ui_lang(st.session_state)
    top_left, top_right = st.columns([3, 1])
    with top_right:
        st.selectbox(
            _t("ui_language"),
            options=["fr", "en"],
            format_func=lambda x: "Français" if x == "fr" else "English",
            key="ui_lang",
        )

    _, center, _ = st.columns([0.2, 3.4, 0.2])
    with center:
        brand_logo, brand_title = st.columns([0.85, 2.15], vertical_alignment="center")
        with brand_logo:
            st.image(str(LOGO_PATH), width=200)
        with brand_title:
            render_brand_subtitle(variant="login")
        st.markdown(
            f'<p class="telnek-login-title">{_t("login_required")}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<span class="telnek-login-caption">{_t("login_caption")}</span>',
            unsafe_allow_html=True,
        )

        with st.form(key="login_form", clear_on_submit=False):
            email = st.text_input(
                _t("email"),
                value="",
                placeholder=_t("login_email_placeholder"),
            )
            password = st.text_input(_t("password"), type="password", placeholder="••••••••")
            submitted = st.form_submit_button(
                _t("login_btn"),
                type="primary",
                use_container_width=True,
            )
            if submitted:
                login_user(email, password)

        st.markdown(
            f'<p class="telnek-login-hint">{_t("login_info")}</p>',
            unsafe_allow_html=True,
        )


def render_app_footer() -> None:
    st.divider()
    st.markdown(
        f'<p class="telnek-footer">{_t("copyright_footer")}</p>',
        unsafe_allow_html=True,
    )


def stop_app() -> None:
    render_app_footer()
    st.stop()


def init_supabase() -> Client:
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        st.error("❌ **Fichier de secrets Streamlit manquant ou incomplet**", icon="🔐")
        stop_app()
        raise RuntimeError("supabase secrets missing")


supabase: Client = init_supabase()

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "fr"
else:
    normalize_ui_lang(st.session_state)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_role = None
    st.session_state.user_client_id = None
    st.session_state.profile = None


def get_user_profile(email: str):
    if not email:
        return None
    try:
        resp = (
            supabase.table("profiles")
            .select("*")
            .eq("email", email.lower().strip())
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]
    except Exception as e:
        print(f"[profiles] Erreur fetch profile pour {email}: {e}")
    return None


def login_user(email: str, password: str) -> bool:
    try:
        auth_resp = supabase.auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
        if not auth_resp or not auth_resp.user:
            st.error(_t("auth_failed"))
            return False

        profile = get_user_profile(email)
        if not profile:
            st.error(_t("no_profile", email=email))
            supabase.auth.sign_out()
            return False

        role = (profile.get("role") or "client").lower()
        if role not in ("admin", "client"):
            role = "client"

        st.session_state.authenticated = True
        st.session_state.user_email = profile.get("email") or email
        st.session_state.profile = profile
        st.session_state.user_role = role
        st.session_state.user_client_id = profile.get("client_id")
        st.success(_t("connected_as", email=st.session_state.user_email, role=role))
        st.rerun()
        return True
    except Exception as e:
        st.error(_t("login_error", error=str(e)))
        return False


def logout_user() -> None:
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for key in (
        "authenticated",
        "user_email",
        "user_role",
        "user_client_id",
        "profile",
        "main_client_selector",
        "main_nav_page",
        "admin_tab_index",
    ):
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def get_clients():
    role = st.session_state.get("user_role")
    if role == "admin":
        return supabase.table("clients").select("*").execute().data or []
    cid = st.session_state.get("user_client_id")
    if cid:
        return supabase.table("clients").select("*").eq("id", cid).execute().data or []
    return []


def update_client(client_id: str, data: dict):
    return supabase.table("clients").update(data).eq("id", client_id).execute()


st.set_page_config(
    page_title=_t("page_title"),
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

if not st.session_state.get("authenticated", False):
    if st.secrets.get("DEV_BYPASS_AUTH", False):
        bypass_role = str(st.secrets.get("DEV_BYPASS_ROLE", "admin")).lower()
        bypass_client_id = st.secrets.get("DEV_BYPASS_CLIENT_ID", None)
        if bypass_role not in ("admin", "client"):
            bypass_role = "admin"
        st.session_state.authenticated = True
        st.session_state.user_email = f"dev-{bypass_role}@local.test"
        st.session_state.user_role = bypass_role
        st.session_state.user_client_id = (
            bypass_client_id if bypass_role == "client" else None
        )
        st.session_state.profile = {
            "role": bypass_role,
            "email": st.session_state.user_email,
        }
        if bypass_role == "admin":
            st.info(_t("dev_admin"))
        else:
            st.info(_t("dev_client", client_id=bypass_client_id))
        st.rerun()

    inject_brand_css(hide_sidebar=True)
    render_login_page()
    stop_app()

inject_brand_css(hide_sidebar=False)
render_app_header()

clients = get_clients()
if not clients:
    st.error(_t("no_clients"))
    stop_app()

is_admin = st.session_state.get("user_role") == "admin"
clients_sorted = sorted(clients, key=lambda c: c.get("id", "").lower())
client_ids = [c["id"] for c in clients_sorted if c.get("id")]
ensure_nav_page(is_admin, st.session_state)

with st.sidebar:
    st.markdown(f"### {_t('nav_section')}")
    nav_pages = nav_pages_for_role(is_admin)
    nav_page = st.radio(
        _t("nav_section"),
        options=nav_pages,
        format_func=lambda page: nav_page_label(page, _t),
        key="main_nav_page",
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown(f"### {_t('client_section')}")

    if is_admin:
        normalize_client_selector(st.session_state, client_ids)
        selected_client_id = st.selectbox(
            _t("select_client"),
            options=client_ids,
            key="main_client_selector",
            label_visibility="collapsed",
        )
    else:
        selected_client_id = client_ids[0] if client_ids else None
        if selected_client_id:
            company_name = next(
                (
                    c.get("company_name", selected_client_id)
                    for c in clients
                    if c["id"] == selected_client_id
                ),
                selected_client_id,
            )
            st.markdown(f"**{company_name}**")
            st.caption(f"`{selected_client_id}`")

    st.divider()
    normalize_ui_lang(st.session_state)
    st.selectbox(
        _t("ui_language"),
        options=["fr", "en"],
        format_func=lambda x: "Français" if x == "fr" else "English",
        key="ui_lang",
    )
    st.divider()
    st.markdown(f"### {_t('session')}")
    st.markdown(f"**{st.session_state.get('user_email', '—')}**")
    role = st.session_state.get("user_role", "—")
    role_emoji = "🛡️" if role == "admin" else "👤"
    st.markdown(f"{_t('role')} : {role_emoji} **{role}**")
    if st.session_state.get("user_client_id"):
        st.caption(f"{_t('restricted_client')} : `{st.session_state['user_client_id']}`")
    render_password_change_form(
        supabase=supabase,
        t_fn=_t,
        user_email=st.session_state.get("user_email", ""),
    )
    st.divider()
    if st.button(_t("logout"), type="secondary", use_container_width=True):
        logout_user()

if selected_client_id:
    client = next((c for c in clients if c["id"] == selected_client_id), None)
    if client is None:
        st.error(_t("client_not_found"))
        stop_app()

    ctx = AppContext(
        supabase=supabase,
        t_fn=_t,
        is_admin=is_admin,
        client=client,
        selected_client_id=selected_client_id,
        client_tz=pytz.timezone(resolve_client_timezone(client)),
        get_clients=get_clients,
        update_client=update_client,
        stop_app=stop_app,
    )

    if nav_page == NAV_PAGE_GLOBAL:
        render_dashboard_page(ctx)
    elif nav_page == NAV_PAGE_CONFIG:
        render_config_page(ctx)
    elif nav_page == NAV_PAGE_CALLS:
        render_calls_page(ctx)
    elif nav_page == NAV_PAGE_STATS:
        render_stats_page(ctx)
    elif nav_page == "users":
        from views.users import render_users_page

        render_users_page(ctx)

render_app_footer()