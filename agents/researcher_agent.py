"""Researcher agent implementation."""

from __future__ import annotations

import json
from typing import Any, Dict

from .base_agent import AgentResult, BaseAgent


class ResearcherAgent(BaseAgent):
    """Gather and structure findings from model output."""

    def run(self, task: str, context: str = "") -> AgentResult:
        """Produce findings, sources, and summary JSON output."""
        cached = self._check_cache(task, context)
        if cached:
            return cached

        raw = self.call_model(task, context)
        data = self._parse(raw, task)
        result = AgentResult(data=data, raw_output=json.dumps(data), tokens_used=self._estimate_tokens(task, context, raw))
        self._cache_result(task, context, result)
        return result

    def _parse(self, raw: str, task: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw)
            if all(key in parsed for key in ("findings", "sources", "summary")):
                return parsed
        except Exception:
            pass
        return {
            "findings": [f"Analyzed task requirements for '{task}'"],
            "sources": ["internal-knowledge"],
            "summary": raw.strip() or f"Research completed for {task}",
        }
