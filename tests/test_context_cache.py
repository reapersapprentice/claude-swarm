"""Tests for context cache behavior."""

from pathlib import Path

from memory.context_cache import ContextCache


def test_lru_cache_eviction_and_persistence(tmp_path: Path) -> None:
    cache_file = tmp_path / "cache.json"
    cache = ContextCache(max_size=2, file_path=str(cache_file))
    cache.set("a", "1")
    cache.set("b", "2")
    assert cache.get("a") == "1"
    cache.set("c", "3")
    assert cache.get("b") is None

    cache2 = ContextCache(max_size=2, file_path=str(cache_file))
    assert cache2.get("a") == "1"
