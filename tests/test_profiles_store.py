"""Tests for profiles_store helpers."""

import pytest

from profiles_store import (
    fetch_profiles,
    normalize_profile_row,
    profiles_to_editor_rows,
    save_profiles,
)


def test_normalize_profile_row_admin_clears_client_id() -> None:
    row = normalize_profile_row(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "Admin@Example.com",
            "role": "admin",
            "client_id": "electriciens",
        },
        valid_client_ids={"electriciens"},
    )
    assert row["email"] == "admin@example.com"
    assert row["role"] == "admin"
    assert row["client_id"] is None


def test_normalize_profile_row_client_requires_client_id() -> None:
    with pytest.raises(ValueError, match="client_id_required"):
        normalize_profile_row(
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "email": "user@example.com",
                "role": "client",
                "client_id": "",
            },
            valid_client_ids={"electriciens"},
        )


def test_normalize_profile_row_client_unknown_client() -> None:
    with pytest.raises(ValueError, match="client_id_invalid"):
        normalize_profile_row(
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "email": "user@example.com",
                "role": "client",
                "client_id": "missing",
            },
            valid_client_ids={"electriciens"},
        )


def test_profiles_to_editor_rows() -> None:
    rows = profiles_to_editor_rows(
        [
            {
                "id": "abc",
                "email": "a@b.com",
                "role": "client",
                "client_id": "telnekdev",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
    )
    assert rows[0]["email"] == "a@b.com"
    assert rows[0]["client_id"] == "telnekdev"


class _FakeQuery:
    def __init__(self, table: str, store: dict):
        self._table = table
        self._store = store
        self._payload: dict | list | None = None
        self._filters: list[tuple[str, str]] = []
        self._delete = False

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
        self._delete = True
        return self

    def execute(self):
        if self._table == "profiles" and self._delete:
            self._store["profiles"] = [
                row
                for row in self._store.get("profiles", [])
                if not all(row.get(k) == v for k, v in self._filters)
            ]
            return type("R", (), {"data": []})()
        if self._table == "profiles" and isinstance(self._payload, dict):
            if "email" in self._payload and any(
                f[0] == "id" for f in self._filters
            ):
                for row in self._store.setdefault("profiles", []):
                    if all(row.get(k) == v for k, v in self._filters):
                        row.update(self._payload)
                        return type("R", (), {"data": [row]})()
            row = {**self._payload}
            self._store.setdefault("profiles", []).append(row)
            return type("R", (), {"data": [row]})()
        if self._table == "profiles" and self._payload is None:
            rows = self._store.get("profiles", [])
            if self._filters:
                rows = [r for r in rows if all(r.get(k) == v for k, v in self._filters)]
            return type("R", (), {"data": rows})()
        return type("R", (), {"data": []})()


class _FakeSupabase:
    def __init__(self, profiles: list[dict]):
        self._store = {"profiles": profiles}

    def table(self, name: str):
        return _FakeQuery(name, self._store)


def test_fetch_profiles_returns_rows() -> None:
    client = _FakeSupabase(
        [{"id": "1", "email": "a@b.com", "role": "admin", "client_id": None}]
    )
    rows = fetch_profiles(client)
    assert len(rows) == 1


def test_save_profiles_updates_and_deletes() -> None:
    keep_id = "11111111-1111-1111-1111-111111111111"
    drop_id = "22222222-2222-2222-2222-222222222222"
    client = _FakeSupabase(
        [
            {
                "id": keep_id,
                "email": "keep@example.com",
                "role": "admin",
                "client_id": None,
            },
            {
                "id": drop_id,
                "email": "drop@example.com",
                "role": "client",
                "client_id": "electriciens",
            },
        ]
    )
    count = save_profiles(
        client,
        [
            {
                "id": keep_id,
                "email": "keep@example.com",
                "role": "admin",
                "client_id": "",
            }
        ],
        existing_ids={keep_id, drop_id},
        valid_client_ids={"electriciens"},
    )
    assert count == 1
    assert len(client._store["profiles"]) == 1
    assert client._store["profiles"][0]["id"] == keep_id