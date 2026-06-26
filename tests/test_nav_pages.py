from ui.nav import (
    ADMIN_NAV_PAGES,
    CLIENT_NAV_PAGES,
    NAV_PAGE_ACCOUNT,
    NAV_PAGE_GLOBAL,
    NAV_PAGE_USERS,
    default_nav_page,
    nav_page_label,
    nav_pages_for_role,
)


def test_admin_nav_includes_global_dashboard() -> None:
    pages = nav_pages_for_role(True)
    assert pages == ADMIN_NAV_PAGES
    assert NAV_PAGE_GLOBAL in pages
    assert NAV_PAGE_USERS in pages


def test_client_nav_excludes_user_management() -> None:
    assert NAV_PAGE_USERS not in nav_pages_for_role(False)


def test_client_nav_excludes_global_dashboard() -> None:
    pages = nav_pages_for_role(False)
    assert pages == CLIENT_NAV_PAGES
    assert NAV_PAGE_GLOBAL not in pages


def test_default_nav_page_by_role() -> None:
    assert default_nav_page(True) == NAV_PAGE_GLOBAL
    assert default_nav_page(False) == "config"


def test_nav_page_label_uses_translation_keys() -> None:
    assert nav_page_label(NAV_PAGE_GLOBAL, lambda key: key) == "tab_global"


def test_account_page_in_nav_for_all_roles() -> None:
    assert NAV_PAGE_ACCOUNT in nav_pages_for_role(True)
    assert NAV_PAGE_ACCOUNT in nav_pages_for_role(False)