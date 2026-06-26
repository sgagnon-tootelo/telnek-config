"""Sidebar widget session-state normalization."""

from __future__ import annotations


def normalize_client_selector(session_state, client_ids: list[str]) -> None:
    if not client_ids:
        return
    current = session_state.get("main_client_selector")
    if current not in client_ids:
        session_state.main_client_selector = client_ids[0]