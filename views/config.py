"""Client configuration page with collapsible sections."""

from __future__ import annotations

import json

import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from i18n import (
    PRIMARY_LANGUAGES,
    TIMEZONE_OPTIONS,
    get_ui_lang,
    normalize_primary_language,
    primary_language_label,
    resolve_client_timezone,
    timezone_label,
)

from app_context import AppContext


def _safe_json_loads(data):
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}
    return data or {}


def _safe_json_dumps(data):
    return json.dumps(_safe_json_loads(data), indent=4, ensure_ascii=False)


def _save_client_config(
    ctx: AppContext,
    *,
    primary_language_selected: str,
    timezone_selected: str,
    company_name: str,
    company_address: str,
    company_hours: str,
    opening_hour: int,
    closing_hour: int,
    admin_phones_edited: str,
    instructions_specific: str,
    base_url: str,
    url_map_edited: str,
    agent_name: str,
    tts_provider_selected: str,
    voice_value: str,
    grok_custom_voice_id: str,
    transfer_mode_selected: str,
    transfer_numbers_edited: str,
    get_caller_history_flag: bool,
    call_transcription_flag: bool,
    confirmation_required: bool,
    hangup_message_flag: bool,
) -> None:
    t = ctx.t_fn
    client = ctx.client

    try:
        url_map_parsed = json.loads(url_map_edited) if url_map_edited.strip() else {}
    except json.JSONDecodeError:
        st.error(t("url_map_invalid"))
        ctx.stop_app()

    transfer_numbers_parsed: dict = {}
    if transfer_mode_selected != "none":
        try:
            transfer_numbers_parsed = (
                json.loads(transfer_numbers_edited) if transfer_numbers_edited.strip() else {}
            )
        except json.JSONDecodeError:
            st.error(t("transfer_json_invalid"))
            ctx.stop_app()
    else:
        transfer_numbers_parsed = client.get("transfer_numbers", {}) or {}

    admin_phones_list = [
        num.strip() for num in admin_phones_edited.splitlines() if num.strip()
    ]

    updated_data = {
        "primary_language": primary_language_selected,
        "timezone": timezone_selected,
        "company_name": company_name,
        "company_address": company_address,
        "company_hours": company_hours,
        "opening_hour": opening_hour,
        "closing_hour": closing_hour,
        "admin_phones": admin_phones_list,
        "instructions_specific": instructions_specific,
        "base_url": base_url,
        "url_map": url_map_parsed,
        "agent_name": agent_name,
        "tts_provider": tts_provider_selected,
        "voice_name": voice_value if tts_provider_selected == "xai" else client.get("voice_name", "ara"),
        "elevenlabs_voice_id": voice_value if tts_provider_selected == "elevenlabs" else None,
        "grok_custom_voice_id": grok_custom_voice_id if tts_provider_selected == "xai" else None,
        "transfer_mode": transfer_mode_selected,
        "transfer_numbers": transfer_numbers_parsed,
        "get_caller_history_flag": get_caller_history_flag,
        "call_transcription_flag": call_transcription_flag,
        "confirmation_required": confirmation_required,
        "hangup_message_flag": hangup_message_flag,
    }
    ctx.update_client(ctx.selected_client_id, updated_data)
    st.success(t("save_ok"))
    st.rerun()


def render_config_page(ctx: AppContext) -> None:
    t = ctx.t_fn
    client = ctx.client
    client_id = ctx.selected_client_id

    st.subheader(t("config_for", client_id=client_id))

    ui_lang = get_ui_lang(st.session_state)

    with st.expander(t("config_section_locale_company"), expanded=True):
        col_lang, col_tz = st.columns(2)
        current_lang = normalize_primary_language(client.get("primary_language"))
        lang_options = [o["value"] for o in PRIMARY_LANGUAGES]
        with col_lang:
            primary_language_selected = st.selectbox(
                t("primary_language"),
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
                t("timezone"),
                options=tz_options,
                format_func=lambda v: timezone_label(v, ui_lang),
                index=tz_options.index(current_tz) if current_tz in tz_options else 0,
            )
        st.caption(
            t("locale_hint_en")
            if primary_language_selected == "en-US"
            else t("locale_hint_fr")
        )

        company_name = st.text_input(t("company_name"), value=client.get("company_name", ""))
        company_address = st.text_input(
            t("company_address"), value=client.get("company_address", "")
        )
        company_hours = st.text_input(t("company_hours"), value=client.get("company_hours", ""))
        col_open, col_close = st.columns(2)
        with col_open:
            opening_hour = st.number_input(
                t("opening_hour"),
                value=client.get("opening_hour", 9),
                min_value=0,
                max_value=23,
                step=1,
            )
        with col_close:
            closing_hour = st.number_input(
                t("closing_hour"),
                value=client.get("closing_hour", 17),
                min_value=0,
                max_value=24,
                step=1,
            )

    with st.expander(t("config_section_notifications"), expanded=False):
        st.caption(t("sms_caption"))
        admin_phones_raw = client.get("admin_phones")
        if isinstance(admin_phones_raw, list):
            current_phones = "\n".join(
                str(p).strip() for p in admin_phones_raw if str(p).strip()
            )
        elif isinstance(admin_phones_raw, str) and admin_phones_raw.strip():
            current_phones = admin_phones_raw
        else:
            current_phones = client.get("admin_phone", "")
        admin_phones_edited = st.text_area(
            t("sms_phones"),
            value=current_phones,
            height=120,
            help="Exemple :\n+15149474976\n+15145551234",
        )
        st.text_input(
            t("virtual_number"),
            value=client.get("callee_number", ""),
            disabled=True,
        )

    with st.expander(t("config_section_agent"), expanded=False):
        instructions_specific = st.text_area(
            t("instructions"),
            value=client.get("instructions_specific", ""),
            height=120,
        )
        base_url = st.text_input(t("website"), value=client.get("base_url", ""))
        url_map_edited = st.text_area(
            t("url_map"),
            value=_safe_json_dumps(client.get("url_map", {})),
            height=150,
        )
        if st.button(t("validate_json"), key=f"validate_url_map_{client_id}"):
            try:
                json.loads(url_map_edited)
                st.success(t("json_valid"))
                st.json(json.loads(url_map_edited))
            except json.JSONDecodeError as e:
                st.error(t("json_invalid", error=e))

        default_agent = "Emily" if primary_language_selected == "en-US" else "Amélie"
        agent_name = st.text_input(
            t("agent_name"),
            value=client.get("agent_name") or default_agent,
        )

        voices_response = (
            ctx.supabase.table("voices")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        all_voices = voices_response.data or []
        grok_voices = [v for v in all_voices if v["provider"] == "grok"]
        eleven_voices = [v for v in all_voices if v["provider"] == "elevenlabs"]

        tts_provider_options = [
            {"value": "xai", "label": t("tts_xai")},
            {"value": "elevenlabs", "label": t("tts_eleven")},
        ]
        current_tts = client.get("tts_provider", "xai")
        default_tts_index = next(
            (i for i, opt in enumerate(tts_provider_options) if opt["value"] == current_tts),
            0,
        )
        selected_tts = st.selectbox(
            t("tts_provider"),
            options=tts_provider_options,
            format_func=lambda x: x["label"],
            index=default_tts_index,
        )
        tts_provider_selected = selected_tts["value"]

        if tts_provider_selected == "xai":
            st.caption(t("grok_caption"))
            voice_options = [
                {"value": v["voice_key"], "label": v["display_label"]} for v in grok_voices
            ]
            default_voice = "eve" if primary_language_selected == "en-US" else "ara"
            current_voice_key = client.get("voice_name") or default_voice
            default_voice_index = next(
                (i for i, opt in enumerate(voice_options) if opt["value"] == current_voice_key),
                0,
            )
            selected_voice = st.selectbox(
                t("grok_standard"),
                options=voice_options,
                format_func=lambda x: x["label"],
                index=default_voice_index,
            )
            grok_custom_raw = st.text_input(
                t("grok_custom"),
                value=client.get("grok_custom_voice_id", "") or "",
                placeholder="ex: custom_abc123...",
                help=t("grok_custom_help"),
            )
            grok_custom_voice_id = grok_custom_raw.strip() if grok_custom_raw else ""
            if grok_custom_voice_id:
                voice_value = grok_custom_voice_id
                st.success(t("grok_custom_active"))
            else:
                voice_value = selected_voice["value"]
        else:
            voice_options = [
                {"value": v["voice_key"], "label": v["display_label"]} for v in eleven_voices
            ]
            current_voice_key = client.get(
                "elevenlabs_voice_id",
                voice_options[0]["value"] if voice_options else "",
            )
            default_voice_index = next(
                (i for i, opt in enumerate(voice_options) if opt["value"] == current_voice_key),
                0,
            )
            selected_voice = st.selectbox(
                t("eleven_voice"),
                options=voice_options,
                format_func=lambda x: x["label"],
                index=default_voice_index,
            )
            voice_value = selected_voice["value"]
            grok_custom_voice_id = ""

    with st.expander(t("config_section_transfer"), expanded=False):
        transfer_mode_options = [
            {"value": "blind", "label": t("transfer_blind")},
            {"value": "warm", "label": t("transfer_warm")},
            {"value": "none", "label": t("transfer_none")},
        ]
        current_mode = client.get("transfer_mode", "none")
        default_mode_index = next(
            (i for i, opt in enumerate(transfer_mode_options) if opt["value"] == current_mode),
            2,
        )
        selected_mode = st.selectbox(
            t("transfer_section"),
            options=transfer_mode_options,
            format_func=lambda x: x["label"],
            index=default_mode_index,
        )
        transfer_mode_selected = selected_mode["value"]

        transfer_numbers_edited = "{}"
        if transfer_mode_selected != "none":
            transfer_numbers_edited = st.text_area(
                t("transfer_numbers"),
                value=_safe_json_dumps(client.get("transfer_numbers", {})),
                height=150,
            )
            if st.button(t("validate_transfer_json"), key=f"validate_transfer_{client_id}"):
                try:
                    json.loads(transfer_numbers_edited)
                    st.success(t("json_valid"))
                    st.json(json.loads(transfer_numbers_edited))
                except json.JSONDecodeError as e:
                    st.error(t("json_invalid", error=e))

    with st.expander(t("config_section_options"), expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            get_caller_history_flag = st.toggle(
                t("toggle_memory"),
                value=client.get("get_caller_history_flag", False),
            )
            call_transcription_flag = st.toggle(
                t("toggle_transcription"),
                value=client.get("call_transcription_flag", False),
            )
        with col2:
            confirmation_required = st.toggle(
                t("toggle_confirmation"),
                value=client.get("confirmation_required", True),
            )
            hangup_message_flag = st.toggle(
                t("toggle_hangup_sms"),
                value=client.get("hangup_message_flag", False),
            )

    with st.expander(t("config_section_google"), expanded=False):
        fresh_client = next(
            (c for c in ctx.get_clients() if c["id"] == client_id),
            client,
        )
        has_google = bool(fresh_client.get("google_refresh_token"))
        col_connect, col_disconnect = st.columns([3, 2])
        with col_connect:
            if has_google:
                st.success(t("google_connected"))
            elif st.button(t("google_connect"), type="primary", key=f"google_connect_{client_id}"):
                scopes = ["https://www.googleapis.com/auth/calendar"]
                flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", scopes=scopes)
                credentials = flow.run_local_server(port=8502, prompt="consent")
                if credentials and credentials.refresh_token:
                    ctx.supabase.table("clients").update(
                        {"google_refresh_token": credentials.refresh_token}
                    ).eq("id", client_id).execute()
                    st.success(t("google_connected_ok"))
                    st.rerun()
                else:
                    st.error(t("google_no_token"))
        with col_disconnect:
            if has_google and st.button(
                t("google_disconnect"),
                type="secondary",
                key=f"google_disconnect_{client_id}",
            ):
                ctx.supabase.table("clients").update(
                    {"google_refresh_token": None}
                ).eq("id", client_id).execute()
                st.success(t("google_removed"))
                st.rerun()

    st.markdown('<div class="telnek-config-save-bar">', unsafe_allow_html=True)
    if st.button(t("save_config"), type="primary", use_container_width=True, key=f"save_config_{client_id}"):
        _save_client_config(
            ctx,
            primary_language_selected=primary_language_selected,
            timezone_selected=timezone_selected,
            company_name=company_name,
            company_address=company_address,
            company_hours=company_hours,
            opening_hour=opening_hour,
            closing_hour=closing_hour,
            admin_phones_edited=admin_phones_edited,
            instructions_specific=instructions_specific,
            base_url=base_url,
            url_map_edited=url_map_edited,
            agent_name=agent_name,
            tts_provider_selected=tts_provider_selected,
            voice_value=voice_value,
            grok_custom_voice_id=grok_custom_voice_id,
            transfer_mode_selected=transfer_mode_selected,
            transfer_numbers_edited=transfer_numbers_edited,
            get_caller_history_flag=get_caller_history_flag,
            call_transcription_flag=call_transcription_flag,
            confirmation_required=confirmation_required,
            hangup_message_flag=hangup_message_flag,
        )
    st.markdown("</div>", unsafe_allow_html=True)