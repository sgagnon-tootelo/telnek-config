"""Sidebar navigation constants and helpers."""

NAV_PAGE_GLOBAL = "global"
NAV_PAGE_CONFIG = "config"
NAV_PAGE_CALLS = "calls"
NAV_PAGE_STATS = "stats"

ADMIN_NAV_PAGES = [
    NAV_PAGE_GLOBAL,
    NAV_PAGE_CONFIG,
    NAV_PAGE_CALLS,
    NAV_PAGE_STATS,
]
CLIENT_NAV_PAGES = [
    NAV_PAGE_CONFIG,
    NAV_PAGE_CALLS,
    NAV_PAGE_STATS,
]

NAV_PAGE_LABEL_KEYS = {
    NAV_PAGE_GLOBAL: "tab_global",
    NAV_PAGE_CONFIG: "tab_config",
    NAV_PAGE_CALLS: "tab_calls",
    NAV_PAGE_STATS: "tab_stats",
}


def nav_pages_for_role(is_admin: bool) -> list[str]:
    return ADMIN_NAV_PAGES if is_admin else CLIENT_NAV_PAGES


def default_nav_page(is_admin: bool) -> str:
    return NAV_PAGE_GLOBAL if is_admin else NAV_PAGE_CONFIG


def nav_page_label(page: str, t_fn) -> str:
    return t_fn(NAV_PAGE_LABEL_KEYS[page])


def ensure_nav_page(is_admin: bool, session_state) -> None:
    allowed = nav_pages_for_role(is_admin)
    current = session_state.get("main_nav_page")
    if current not in allowed:
        session_state.main_nav_page = default_nav_page(is_admin)