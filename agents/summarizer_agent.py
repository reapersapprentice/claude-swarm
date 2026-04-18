"""Summarizer agent implementation."""

from __future__ import annotations

import json
from typing import Any, Dict

from .base_agent import AgentResult, BaseAgent


class SummarizerAgent(BaseAgent):
    """Compress outputs for final delivery."""

    def run(self, task: str, context: str = "") -> AgentResult:
        """Produce compact merged summary output."""
        cached = self._check_cache(task, context)
        if cached:
            return cached

        raw = self.call_model(task, context)
        data = self._parse(raw, context)
        result = AgentResult(data=data, raw_output=json.dumps(data), tokens_used=self._estimate_tokens(task, context, raw))
        self._cache_result(task, context, result)
        return result

    def _parse(self, raw: str, context: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        summary = raw.strip() or " ".join(context.split()[:120])
        return {"summary": summary}
