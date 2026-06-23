"""Shared runtime context passed to page renderers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from supabase import Client

TranslateFn = Callable[..., str]


@dataclass(frozen=True)
class AppContext:
    supabase: Client
    t_fn: TranslateFn
    is_admin: bool
    client: dict[str, Any]
    selected_client_id: str
    client_tz: Any
    get_clients: Callable[[], list[dict[str, Any]]]
    update_client: Callable[[str, dict[str, Any]], Any]
    stop_app: Callable[[], None]