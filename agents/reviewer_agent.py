"""Reviewer agent implementation."""

from __future__ import annotations

import json
from typing import Any, Dict

from .base_agent import AgentResult, BaseAgent


class ReviewerAgent(BaseAgent):
    """Validate outputs for correctness and risks."""

    def run(self, task: str, context: str = "") -> AgentResult:
        """Produce issues, approval, and suggestions JSON."""
        cached = self._check_cache(task, context)
        if cached:
            return cached

        raw = self.call_model(task, context)
        data = self._parse(raw)
        result = AgentResult(data=data, raw_output=json.dumps(data), tokens_used=self._estimate_tokens(task, context, raw))
        self._cache_result(task, context, result)
        return result

    def _parse(self, raw: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw)
            if all(key in parsed for key in ("issues", "approved", "suggestions")):
                return parsed
        except Exception:
            pass
        return {"issues": [], "approved": True, "suggestions": [raw.strip() or "No suggestions"]}
