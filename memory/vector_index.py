"""Simple in-memory vector index using bag-of-words cosine similarity."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class VectorEntry:
    """Stored text chunk and sparse vector."""

    key: str
    text: str
    vector: Dict[str, float]


class VectorIndex:
    """In-memory vector similarity search without external dependencies."""

    def __init__(self) -> None:
        self._entries: List[VectorEntry] = []

    def add(self, key: str, text: str) -> None:
        """Index text under key."""
        vector = self._to_vector(text)
        self._entries.append(VectorEntry(key=key, text=text, vector=vector))

    def search(self, query: str, top_k: int = 3) -> List[VectorEntry]:
        """Return top-k most similar indexed entries."""
        query_vec = self._to_vector(query)
        ranked = sorted(
            self._entries,
            key=lambda entry: self._cosine_similarity(query_vec, entry.vector),
            reverse=True,
        )
        return ranked[:top_k]

    def _to_vector(self, text: str) -> Dict[str, float]:
        tokens = re.findall(r"\w+", text.lower())
        counts = Counter(tokens)
        length = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {token: value / length for token, value in counts.items()}

    def _cosine_similarity(self, left: Dict[str, float], right: Dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        smaller, larger = (left, right) if len(left) <= len(right) else (right, left)
        return sum(weight * larger.get(token, 0.0) for token, weight in smaller.items())
