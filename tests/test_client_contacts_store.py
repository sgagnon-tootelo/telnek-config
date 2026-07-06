"""Tests for client_contacts_store helpers."""

from client_contacts_store import (
    build_transfer_numbers,
    contacts_to_editor_rows,
    ensure_unique_slug,
    normalize_contact_row,
    normalize_phone_extension,
    parse_keywords,
    save_client_contacts,
    slugify,
)


def test_slugify_normalizes_accents() -> None:
    assert slugify("Comptabilité") == "comptabilite"


def test_parse_keywords_from_comma_string() -> None:
    assert parse_keywords("vente, support, facturation") == ["vente", "support", "facturation"]


def test_build_transfer_numbers_sorted_by_priority() -> None:
    contacts = [
        {"display_name": "B", "phone_e164": "+15141111111", "priority": 200, "active": True, "can_transfer": True},
        {"display_name": "A", "phone_e164": "+15142222222", "priority": 100, "active": True, "can_transfer": True},
    ]
    assert build_transfer_numbers(contacts) == {
        "A": "+15142222222",
        "B": "+15141111111",
    }


def test_normalize_contact_row_requires_phone_when_transferable() -> None:
    try:
        normalize_contact_row({"display_name": "Ventes", "can_transfer": True})
        raised = False
    except ValueError as exc:
        raised = True
        assert str(exc) == "phone_required_for_transfer"
    assert raised


def test_normalize_contact_row_requires_phone_when_notify_enabled() -> None:
    try:
        normalize_contact_row(
            {
                "display_name": "Marjolaine",
                "can_transfer": False,
                "notify_message": True,
            }
        )
        raised = False
    except ValueError as exc:
        raised = True
        assert str(exc) == "phone_required_for_notify"
    assert raised


def test_contacts_to_editor_rows_flattens_keywords() -> None:
    rows = contacts_to_editor_rows(
        [{"id": "x", "display_name": "Ventes", "keywords": ["a", "b"], "priority": 10, "active": True}]
    )
    assert rows[0]["keywords"] == "a, b"
    assert rows[0]["display_name"] == "Ventes"


def test_normalize_phone_extension_strips_label() -> None:
    assert normalize_phone_extension("poste 201") == "201"
    assert normalize_phone_extension("") is None


def test_contacts_to_editor_rows_includes_phone_ext() -> None:
    rows = contacts_to_editor_rows(
        [{"id": "x", "display_name": "Sylvain", "phone_e164": "+15149474976", "phone_ext": "201"}]
    )
    assert rows[0]["phone_ext"] == "201"


def test_contacts_to_editor_rows_includes_email_enabled() -> None:
    rows = contacts_to_editor_rows(
        [
            {
                "id": "x",
                "display_name": "Sylvain",
                "email": "admin@example.com",
                "email_enabled": True,
            }
        ]
    )
    assert rows[0]["email"] == "admin@example.com"
    assert rows[0]["email_enabled"] is True


def test_normalize_contact_row_requires_email_when_email_enabled() -> None:
    try:
        normalize_contact_row(
            {
                "display_name": "Sylvain",
                "can_transfer": False,
                "notify_transfer_fail": False,
                "email_enabled": True,
            }
        )
        raised = False
    except ValueError as exc:
        raised = True
        assert str(exc) == "email_required_for_notify"
    assert raised


class _FakeQuery:
    def __init__(self, table: str, store: dict):
        self._table = table
        self._store = store
        self._payload: dict | None = None
        self._filters: list[tuple[str, str]] = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key: str, value: str):
        self._filters.append((key, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def update(self, payload: dict):
        self._payload = payload
        return self

    def insert(self, payload: dict):
        self._payload = payload
        return self

    def delete(self):
        return self

    def execute(self):
        if self._table == "client_contacts" and self._payload and "client_id" in self._payload:
            row = {**self._payload, "id": "new-id"}
            self._store.setdefault("client_contacts", []).append(row)
            return type("R", (), {"data": [row]})()
        if self._table == "clients" and self._payload:
            self._store["clients_transfer"] = self._payload.get("transfer_numbers")
            return type("R", (), {"data": []})()
        if self._table == "client_contacts" and not self._payload:
            rows = [
                r
                for r in self._store.get("client_contacts", [])
                if all(r.get(k) == v for k, v in self._filters)
            ]
            return type("R", (), {"data": rows})()
        return type("R", (), {"data": []})()


class _FakeSupabase:
    def __init__(self):
        self._store: dict = {}

    def table(self, name: str):
        return _FakeQuery(name, self._store)


def test_save_client_contacts_inserts_and_syncs_transfer_numbers() -> None:
    client = _FakeSupabase()
    transfer_map = save_client_contacts(
        client,
        "telnekdev",
        [
            {
                "display_name": "Ventes",
                "slug": "vente",
                "phone_e164": "+15149474976",
                "can_transfer": True,
                "active": True,
                "priority": 100,
            }
        ],
        existing_ids=set(),
    )
    assert transfer_map == {"Ventes": "+15149474976"}
    assert client._store["clients_transfer"] == {"Ventes": "+15149474976"}


def test_ensure_unique_slug_appends_suffix() -> None:
    used: set[str] = set()
    assert ensure_unique_slug("vente", used) == "vente"
    assert ensure_unique_slug("vente", used) == "vente-2"