"""JSON-backed namespace-aware key-value knowledge store."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any, Dict


class KnowledgeStore:
    """Persistent key-value store for cross-session knowledge."""

    def __init__(self, file_path: str = "knowledge_store/store.json") -> None:
        self.file_path = Path(file_path)
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def set(self, namespace: str, key: str, value: Any) -> None:
        """Store key-value in namespace."""
        self._data.setdefault(namespace, {})[key] = value
        self._save()

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """Retrieve value from namespace."""
        return self._data.get(namespace, {}).get(key, default)

    def search(self, namespace: str, key_pattern: str) -> Dict[str, Any]:
        """Find values by wildcard key pattern within namespace."""
        return {
            key: value
            for key, value in self._data.get(namespace, {}).items()
            if fnmatch.fnmatch(key, key_pattern)
        }

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        self._data = json.loads(self.file_path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
