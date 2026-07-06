"""Supabase client_contacts CRUD and transfer_numbers sync for telnek-config."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

CONTACT_TYPES = ("department", "person")


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.strip().lower())
    return slug.strip("-") or "contact"


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in ("none", "nan"):
        return ""
    return text


def _clean_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "oui"):
        return True
    if text in ("false", "0", "no", "non", ""):
        return False
    return default


def normalize_phone_extension(value: Any) -> str | None:
    raw = _clean_str(value)
    if not raw:
        return None
    digits = "".join(c for c in raw if c.isdigit())
    return digits or None


def _clean_int(value: Any, default: int = 100) -> int:
    if value is None or str(value).strip().lower() in ("", "none", "nan"):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(k).strip() for k in value if str(k).strip()]
    raw = _clean_str(value)
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def keywords_to_display(value: Any) -> str:
    return ", ".join(parse_keywords(value))


def ensure_unique_slug(base_slug: str, used: set[str]) -> str:
    slug = base_slug or "contact"
    if slug not in used:
        used.add(slug)
        return slug
    index = 2
    while f"{slug}-{index}" in used:
        index += 1
    unique = f"{slug}-{index}"
    used.add(unique)
    return unique


def normalize_contact_row(row: dict[str, Any], *, used_slugs: set[str] | None = None) -> dict[str, Any]:
    display_name = _clean_str(row.get("display_name"))
    if not display_name:
        raise ValueError("display_name_required")

    slug_raw = _clean_str(row.get("slug")) or slugify(display_name)
    slug_set = used_slugs if used_slugs is not None else set()
    slug = ensure_unique_slug(slugify(slug_raw) or slugify(display_name), slug_set)

    contact_type = _clean_str(row.get("contact_type")) or "department"
    if contact_type not in CONTACT_TYPES:
        contact_type = "department"

    can_transfer = _clean_bool(row.get("can_transfer"), default=True)
    notify_message = _clean_bool(row.get("notify_message"), default=False)
    notify_rdv = _clean_bool(row.get("notify_rdv"), default=False)
    notify_transfer_fail = _clean_bool(row.get("notify_transfer_fail"), default=True)
    phone = _clean_str(row.get("phone_e164")) or None
    email = _clean_str(row.get("email")) or None
    email_enabled = _clean_bool(row.get("email_enabled"), default=False)
    if can_transfer and not phone:
        raise ValueError("phone_required_for_transfer")
    if (notify_message or notify_rdv or notify_transfer_fail) and not phone:
        raise ValueError("phone_required_for_notify")
    if email_enabled and not email:
        raise ValueError("email_required_for_notify")

    return {
        "id": _clean_str(row.get("id")) or None,
        "display_name": display_name,
        "slug": slug,
        "contact_type": contact_type,
        "phone_e164": phone,
        "phone_ext": normalize_phone_extension(row.get("phone_ext")),
        "email": email,
        "sms_enabled": _clean_bool(row.get("sms_enabled"), default=True),
        "email_enabled": email_enabled,
        "can_transfer": can_transfer,
        "notify_message": notify_message,
        "notify_rdv": notify_rdv,
        "notify_transfer_fail": notify_transfer_fail,
        "keywords": parse_keywords(row.get("keywords")),
        "priority": _clean_int(row.get("priority"), default=100),
        "active": _clean_bool(row.get("active"), default=True),
        "notes": _clean_str(row.get("notes")) or None,
    }


def build_transfer_numbers(contacts: list[dict[str, Any]]) -> dict[str, str]:
    transferable = [
        c
        for c in contacts
        if c.get("active", True) and c.get("can_transfer", True) and c.get("phone_e164")
    ]
    transferable.sort(key=lambda c: (_clean_int(c.get("priority")), _clean_str(c.get("display_name")).lower()))
    return {c["display_name"]: c["phone_e164"] for c in transferable}


def contacts_to_editor_rows(contacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for contact in contacts:
        rows.append(
            {
                "id": contact.get("id") or "",
                "display_name": contact.get("display_name") or "",
                "slug": contact.get("slug") or "",
                "contact_type": contact.get("contact_type") or "department",
                "phone_e164": contact.get("phone_e164") or "",
                "phone_ext": contact.get("phone_ext") or "",
                "email": contact.get("email") or "",
                "email_enabled": bool(contact.get("email_enabled", False)),
                "can_transfer": bool(contact.get("can_transfer", True)),
                "notify_message": bool(contact.get("notify_message", False)),
                "notify_rdv": bool(contact.get("notify_rdv", False)),
                "notify_transfer_fail": bool(contact.get("notify_transfer_fail", True)),
                "keywords": keywords_to_display(contact.get("keywords")),
                "priority": _clean_int(contact.get("priority"), default=100),
                "active": bool(contact.get("active", True)),
            }
        )
    return rows


def fetch_client_contacts(supabase: Any, client_id: str, *, include_inactive: bool = True) -> list[dict[str, Any]]:
    query = supabase.table("client_contacts").select("*").eq("client_id", client_id)
    if not include_inactive:
        query = query.eq("active", True)
    response = query.order("priority").order("display_name").execute()
    return response.data or []


def save_client_contacts(
    supabase: Any,
    client_id: str,
    editor_rows: list[dict[str, Any]],
    *,
    existing_ids: set[str] | None = None,
) -> dict[str, str]:
    used_slugs: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for row in editor_rows:
        if not _clean_str(row.get("display_name")) and not _clean_str(row.get("phone_e164")):
            continue
        normalized.append(normalize_contact_row(row, used_slugs=used_slugs))

    kept_ids = {c["id"] for c in normalized if c.get("id")}
    to_delete = (existing_ids or set()) - kept_ids

    for contact_id in to_delete:
        supabase.table("client_contacts").delete().eq("id", contact_id).eq("client_id", client_id).execute()

    saved: list[dict[str, Any]] = []
    for contact in normalized:
        payload = {
            "client_id": client_id,
            "display_name": contact["display_name"],
            "slug": contact["slug"],
            "contact_type": contact["contact_type"],
            "phone_e164": contact["phone_e164"],
            "phone_ext": contact["phone_ext"],
            "email": contact["email"],
            "sms_enabled": contact["sms_enabled"],
            "email_enabled": contact["email_enabled"],
            "can_transfer": contact["can_transfer"],
            "notify_message": contact["notify_message"],
            "notify_rdv": contact["notify_rdv"],
            "notify_transfer_fail": contact["notify_transfer_fail"],
            "keywords": contact["keywords"],
            "priority": contact["priority"],
            "active": contact["active"],
            "notes": contact["notes"],
        }
        if contact.get("id"):
            response = (
                supabase.table("client_contacts")
                .update(payload)
                .eq("id", contact["id"])
                .eq("client_id", client_id)
                .execute()
            )
            saved.extend(response.data or [])
        else:
            response = supabase.table("client_contacts").insert(payload).execute()
            saved.extend(response.data or [])

    transfer_map = build_transfer_numbers(normalized)
    supabase.table("clients").update({"transfer_numbers": transfer_map}).eq("id", client_id).execute()
    return transfer_map