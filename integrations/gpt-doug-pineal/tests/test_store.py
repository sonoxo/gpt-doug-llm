import sqlite3

import pytest

from pineal.store import ConflictError, NotFoundError, PinealStore


def test_create_read_update_delete_and_audit(tmp_path):
    store = PinealStore(tmp_path / "db.sqlite3")
    row = store.put(namespace="project", subject="gpt-doug", predicate="has_layer",
                    value="pineal", source="user-approved design", confidence=0.9)
    assert row["version"] == 1
    assert store.get(row["id"])["value"] == "pineal"
    assert len(store.search(query="PINEAL", namespace="project")) == 1
    with pytest.raises(ConflictError):
        store.put(item_id=row["id"], expected_version=2, subject="gpt-doug",
                  predicate="has_layer", value="kraken")
    updated = store.put(item_id=row["id"], expected_version=1, namespace="project",
                        subject="gpt-doug", predicate="has_layer", value="kraken", source="verified")
    assert updated["version"] == 2
    assert store.search(query="pineal") == []
    with pytest.raises(ConflictError):
        store.delete(row["id"], expected_version=1)
    store.delete(row["id"], expected_version=2)
    with pytest.raises(NotFoundError):
        store.get(row["id"])
    assert store.verify_audit()["ok"]
    assert store.verify_audit()["checked"] == 3


def test_credentials_and_injection_are_rejected(tmp_path):
    store = PinealStore(tmp_path / "db.sqlite3")
    with pytest.raises(ValueError, match="credential"):
        store.put(subject="private", predicate="secret",
                  value="sk-123456789012345678901", source="manual")
    store.put(subject="a%", predicate="literal", value="okay", source="user")
    assert len(store.search(query="a%")) == 1
    assert not store.search(query="'; DROP TABLE memories; --")
    assert store.verify_audit()["ok"]


def test_expiry_and_tamper(tmp_path):
    store = PinealStore(tmp_path / "db.sqlite3")
    row = store.put(subject="brief", predicate="lifetime", value="short", ttl_seconds=10)
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE memories SET expires_at = '2000-01-01T00:00:00+00:00' WHERE id=?", (row["id"],))
    with pytest.raises(NotFoundError):
        store.get(row["id"])
    assert store.heartbeat()["expired"] == 1
    assert store.verify_audit()["ok"]
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE audit SET action = 'evil' WHERE seq=1")
    assert store.verify_audit()["ok"] is False


def test_limits(tmp_path):
    store = PinealStore(tmp_path / "db.sqlite3")
    with pytest.raises(ValueError):
        store.put(subject="", predicate="test", value="data")
    with pytest.raises(ValueError):
        store.put(subject="a", predicate="p", value="data", confidence=float("nan"))
    with pytest.raises(ValueError):
        store.search(limit=101)
