"""Disk-serializable LRU cache for agent context outputs."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional


class ContextCache:
    """LRU cache keyed by agent/task/context hash."""

    def __init__(self, max_size: int = 128, file_path: str = ".swarm_cache") -> None:
        self.max_size = max_size
        self.file_path = Path(file_path)
        self._cache: "OrderedDict[str, str]" = OrderedDict()
        self._load()

    def make_key(self, agent_name: str, task: str, context: str) -> str:
        """Return deterministic cache key for input triple."""
        blob = f"{agent_name}::{task}::{context}".encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def get(self, key: str) -> Optional[str]:
        """Fetch value and bump to most-recently used position."""
        if key not in self._cache:
            return None
        value = self._cache.pop(key)
        self._cache[key] = value
        return value

    def set(self, key: str, value: str) -> None:
        """Store value and evict least-recently used item if needed."""
        if key in self._cache:
            self._cache.pop(key)
        self._cache[key] = value
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
        self._save()

    def clear(self) -> None:
        """Remove all cache entries and persist empty cache."""
        self._cache.clear()
        self._save()

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        data = json.loads(self.file_path.read_text(encoding="utf-8"))
        for key, value in data.items():
            self._cache[key] = value

    def _save(self) -> None:
        self.file_path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
