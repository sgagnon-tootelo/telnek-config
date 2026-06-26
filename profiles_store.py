"""Supabase profiles CRUD for admin user management."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

PROFILE_ROLES = ("admin", "client")
FetchSource = Literal["rpc", "table"]


@dataclass(frozen=True)
class FetchProfilesResult:
    profiles: list[dict[str, Any]]
    source: FetchSource
    rpc_error: str | None = None

    @property
    def has_last_login_data(self) -> bool:
        return any(profile.get("last_sign_in_at") for profile in self.profiles)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in ("none", "nan"):
        return ""
    return text


def normalize_profile_row(
    row: dict[str, Any],
    *,
    valid_client_ids: set[str],
) -> dict[str, Any]:
    profile_id = _clean_str(row.get("id"))
    if not profile_id or not _UUID_RE.match(profile_id):
        raise ValueError("id_invalid")

    email = _clean_str(row.get("email")).lower()
    if not email or "@" not in email:
        raise ValueError("email_required")

    role = _clean_str(row.get("role")).lower() or "client"
    if role not in PROFILE_ROLES:
        raise ValueError("role_invalid")

    client_id = _clean_str(row.get("client_id")) or None
    if role == "admin":
        client_id = None
    elif not client_id:
        raise ValueError("client_id_required")
    elif client_id not in valid_client_ids:
        raise ValueError("client_id_invalid")

    return {
        "id": profile_id,
        "email": email,
        "role": role,
        "client_id": client_id,
    }


def format_last_sign_in(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in ("none", "nan"):
        return ""
    if text.endswith("+00:00"):
        text = f"{text[:-6]}Z"
    if "T" in text:
        date_part, time_part = text.split("T", 1)
        time_part = time_part.replace("Z", "").split("+")[0].split(".")[0]
        return f"{date_part} {time_part} UTC"
    return text


def profiles_to_editor_rows(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        client_id = profile.get("client_id")
        rows.append(
            {
                "id": profile.get("id") or "",
                "email": profile.get("email") or "",
                "role": profile.get("role") or "client",
                "client_id": "" if client_id is None else str(client_id),
                "created_at": profile.get("created_at") or "",
                "last_sign_in_at": format_last_sign_in(profile.get("last_sign_in_at")),
            }
        )
    return rows


def fetch_profiles(supabase: Any) -> FetchProfilesResult:
    rpc_error: str | None = None
    try:
        response = supabase.rpc("fetch_profiles_for_admin", {}).execute()
        if response.data is not None:
            return FetchProfilesResult(
                profiles=response.data,
                source="rpc",
            )
    except Exception as exc:
        rpc_error = str(exc)

    response = (
        supabase.table("profiles")
        .select("id, email, role, client_id, created_at")
        .order("email")
        .execute()
    )
    return FetchProfilesResult(
        profiles=response.data or [],
        source="table",
        rpc_error=rpc_error,
    )


def save_profiles(
    supabase: Any,
    editor_rows: list[dict[str, Any]],
    *,
    existing_ids: set[str],
    valid_client_ids: set[str],
) -> int:
    normalized: list[dict[str, Any]] = []
    for row in editor_rows:
        if not _clean_str(row.get("id")) and not _clean_str(row.get("email")):
            continue
        normalized.append(
            normalize_profile_row(row, valid_client_ids=valid_client_ids)
        )

    kept_ids = {profile["id"] for profile in normalized}
    to_delete = existing_ids - kept_ids

    for profile_id in to_delete:
        supabase.table("profiles").delete().eq("id", profile_id).execute()

    saved = 0
    for profile in normalized:
        payload = {
            "email": profile["email"],
            "role": profile["role"],
            "client_id": profile["client_id"],
        }
        if profile["id"] in existing_ids:
            supabase.table("profiles").update(payload).eq("id", profile["id"]).execute()
        else:
            supabase.table("profiles").insert({**payload, "id": profile["id"]}).execute()
        saved += 1
    return saved