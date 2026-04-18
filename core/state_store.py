"""Persistent state store with namespace support and TTL expiration."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class StateStore:
    """JSON-backed state storage for swarm execution artifacts."""

    def __init__(self, file_path: str = ".swarm_state.json", default_ttl: Optional[int] = None) -> None:
        self.file_path = Path(file_path)
        self.default_ttl = default_ttl
        self._state: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._load()

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store a value for key under a namespace."""
        namespace_store = self._state.setdefault(namespace, {})
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = int(time.time() + ttl) if ttl else None
        namespace_store[key] = {"value": value, "expires_at": expires_at}
        self._save()

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """Retrieve a value by namespace and key."""
        self._prune_expired()
        value = self._state.get(namespace, {}).get(key)
        if value is None:
            return default
        return value["value"]

    def delete(self, namespace: str, key: str) -> None:
        """Delete a key in a namespace if present."""
        if namespace in self._state and key in self._state[namespace]:
            del self._state[namespace][key]
            self._save()

    def clear_namespace(self, namespace: str) -> None:
        """Clear all entries in a namespace."""
        if namespace in self._state:
            del self._state[namespace]
            self._save()

    def _prune_expired(self) -> None:
        now = int(time.time())
        changed = False
        for namespace in list(self._state.keys()):
            for key in list(self._state[namespace].keys()):
                expires_at = self._state[namespace][key].get("expires_at")
                if expires_at and expires_at <= now:
                    del self._state[namespace][key]
                    changed = True
            if not self._state[namespace]:
                del self._state[namespace]
                changed = True
        if changed:
            self._save()

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        self._state = json.loads(self.file_path.read_text(encoding="utf-8"))
        self._prune_expired()

    def _save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(self._state, indent=2, sort_keys=True), encoding="utf-8")
