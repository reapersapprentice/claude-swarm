"""Semantic/context compression helpers for inter-agent outputs."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Callable, List, Optional


class CompressionPipeline:
    """Apply deduplication and relevance pruning."""

    def __init__(self, estimator: Optional[Callable[[str], int]] = None) -> None:
        self.estimator = estimator or self._default_estimator

    def _default_estimator(self, text: str) -> int:
        return int(len(text.split()) * 1.3) + 1 if text.strip() else 0

    def deduplicate(self, segments: List[str]) -> List[str]:
        """Drop near-duplicate segments."""
        unique: List[str] = []
        fingerprints: List[str] = []
        for segment in segments:
            normalized = " ".join(segment.lower().split())
            if any(SequenceMatcher(a=normalized, b=fp).ratio() > 0.98 for fp in fingerprints):
                continue
            fingerprints.append(normalized)
            unique.append(segment)
        return unique

    def prune(self, text: str, task: str = "", max_tokens: Optional[int] = None) -> str:
        """Keep highest-relevance blocks while respecting token cap."""
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        if not blocks:
            return ""
        task_terms = set(re.findall(r"\w+", task.lower()))

        def score(block: str) -> float:
            words = re.findall(r"\w+", block.lower())
            if not words:
                return 0.0
            overlap = sum(1 for token in words if token in task_terms)
            return overlap / len(words)

        selected: List[str] = []
        for block in sorted(self.deduplicate(blocks), key=score, reverse=True):
            candidate = "\n\n".join(selected + [block])
            if max_tokens is None or self.estimator(candidate) <= max_tokens:
                selected.append(block)
        return "\n\n".join(selected) if selected else blocks[0]

    def compress(self, text: str, task: str = "", max_tokens: Optional[int] = None) -> str:
        """Run full compression pipeline."""
        if not text.strip():
            return ""
        return self.prune(text, task=task, max_tokens=max_tokens)
