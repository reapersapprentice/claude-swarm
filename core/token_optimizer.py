"""Token optimization utilities for context compaction and budget enforcement."""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional


class TokenOptimizer:
    """Apply deterministic token reduction strategies."""

    def __init__(self, config: Optional[Dict[str, int]] = None) -> None:
        cfg = config or {}
        self.max_tokens_per_agent = int(cfg.get("max_tokens_per_agent", 4000))
        self.max_total_tokens = int(cfg.get("max_total_tokens", 50000))
        self.compression_threshold = int(cfg.get("compression_threshold", 1000))
        self.tokens_used = 0
        self._previous_context: Dict[str, str] = {}

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens using words*1.3 approximation."""
        if not text.strip():
            return 0
        return int(math.ceil(len(text.split()) * 1.3))

    def prune_context(self, context: str, max_tokens: int, task: Optional[str] = None) -> str:
        """Remove lowest-relevance context segments to fit target token budget."""
        segments = [seg.strip() for seg in re.split(r"\n\s*\n", context) if seg.strip()]
        if not segments:
            return ""

        task_terms = set(re.findall(r"\w+", (task or "").lower()))

        def score(segment: str) -> float:
            words = re.findall(r"\w+", segment.lower())
            if not words:
                return 0.0
            overlap = sum(1 for w in words if w in task_terms)
            return overlap / max(1, len(words))

        ranked = sorted(segments, key=score, reverse=True)
        selected: List[str] = []
        for segment in ranked:
            candidate = "\n\n".join(selected + [segment])
            if self.estimate_tokens(candidate) <= max_tokens:
                selected.append(segment)
            elif not selected:
                words = segment.split()
                while words and self.estimate_tokens(" ".join(words)) > max_tokens:
                    words.pop()
                selected.append(" ".join(words))
                break
        return "\n\n".join(selected)

    def deduplicate(self, contexts: List[str]) -> List[str]:
        """Remove repeated context entries using normalized comparison."""
        unique: List[str] = []
        normalized_seen: List[str] = []
        for context in contexts:
            normalized = " ".join(context.lower().split())
            if any(SequenceMatcher(a=normalized, b=s).ratio() > 0.98 for s in normalized_seen):
                continue
            normalized_seen.append(normalized)
            unique.append(context)
        return unique

    def incremental_context(self, agent_name: str, context: str) -> str:
        """Return only incremental additions versus the previous context for this agent."""
        previous = self._previous_context.get(agent_name, "")
        if not previous:
            self._previous_context[agent_name] = context
            return context
        if context.startswith(previous):
            delta = context[len(previous):].lstrip()
            self._previous_context[agent_name] = context
            return delta or ""
        self._previous_context[agent_name] = context
        return context

    def compress(self, context: str, task: Optional[str] = None, agent_name: str = "") -> str:
        """Compress context via deduplication, incremental diffing, and pruning."""
        if not context:
            return ""
        compact = "\n\n".join(self.deduplicate([part for part in context.split("\n\n") if part.strip()]))
        if agent_name:
            incremental = self.incremental_context(agent_name, compact)
            compact = incremental or compact
        if self.estimate_tokens(compact) > self.compression_threshold:
            compact = self.prune_context(compact, self.max_tokens_per_agent, task=task)
        return compact

    def enforce_budget(self, estimated_tokens: int, agent_limit: Optional[int] = None) -> None:
        """Raise ValueError if proposed token usage exceeds limits."""
        limit = agent_limit or self.max_tokens_per_agent
        if estimated_tokens > limit:
            raise ValueError(f"Per-agent token limit exceeded ({estimated_tokens}>{limit})")
        if self.tokens_used + estimated_tokens > self.max_total_tokens:
            raise ValueError("Global token budget exceeded")

    def record_usage(self, tokens: int) -> None:
        """Record token usage for global budget tracking."""
        self.tokens_used += tokens
