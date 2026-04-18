"""Comprehensive tests for core/state_store.py."""

import time

import pytest

from core.state_store import StateStore


@pytest.fixture
def store(tmp_path):
    """Create a StateStore backed by a temp file."""
    return StateStore(file_path=str(tmp_path / "state.json"))


@pytest.fixture
def store_path(tmp_path):
    """Return a temp file path for constructing StateStore instances manually."""
    return str(tmp_path / "state.json")


def test_ttl_expiration(store):
    store.set("ns", "key", "value", ttl_seconds=1)
    assert store.get("ns", "key") == "value"
    time.sleep(1.5)
    assert store.get("ns", "key") is None


def test_default_ttl(tmp_path):
    store = StateStore(file_path=str(tmp_path / "state.json"), default_ttl=1)
    store.set("ns", "key", "value")
    assert store.get("ns", "key") == "value"
    time.sleep(1.5)
    assert store.get("ns", "key") is None


def test_no_ttl_never_expires(store):
    store.set("ns", "key", "value")
    time.sleep(1.5)
    assert store.get("ns", "key") == "value"


def test_delete_key(store):
    store.set("ns", "key", "value")
    store.delete("ns", "key")
    assert store.get("ns", "key") is None


def test_delete_key_returns_default(store):
    store.set("ns", "key", "value")
    store.delete("ns", "key")
    assert store.get("ns", "key", default="fallback") == "fallback"


def test_clear_namespace(store):
    store.set("ns", "a", 1)
    store.set("ns", "b", 2)
    store.set("ns", "c", 3)
    store.clear_namespace("ns")
    assert store.get("ns", "a") is None
    assert store.get("ns", "b") is None
    assert store.get("ns", "c") is None


def test_get_missing_namespace(store):
    assert store.get("nonexistent", "key") is None


def test_get_missing_key(store):
    store.set("ns", "existing", "value")
    assert store.get("ns", "missing") is None


def test_get_missing_key_with_default(store):
    assert store.get("ns", "missing", default=42) == 42


def test_persistence(store_path):
    store1 = StateStore(file_path=store_path)
    store1.set("ns", "key", "persisted")

    store2 = StateStore(file_path=store_path)
    assert store2.get("ns", "key") == "persisted"


def test_multiple_namespaces_isolation(store):
    store.set("ns1", "key", "value1")
    store.set("ns2", "key", "value2")
    assert store.get("ns1", "key") == "value1"
    assert store.get("ns2", "key") == "value2"

    store.delete("ns1", "key")
    assert store.get("ns1", "key") is None
    assert store.get("ns2", "key") == "value2"


def test_clear_namespace_does_not_affect_others(store):
    store.set("ns1", "key", "value1")
    store.set("ns2", "key", "value2")
    store.clear_namespace("ns1")
    assert store.get("ns1", "key") is None
    assert store.get("ns2", "key") == "value2"
