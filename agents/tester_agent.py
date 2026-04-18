"""Tester agent implementation."""

from __future__ import annotations

import json
from typing import Any, Dict

from .base_agent import AgentResult, BaseAgent


class TesterAgent(BaseAgent):
    """Generate structured tests and coverage notes."""

    def run(self, task: str, context: str = "") -> AgentResult:
        """Produce tests and coverage notes JSON."""
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
            if all(key in parsed for key in ("tests", "coverage_notes")):
                return parsed
        except Exception:
            pass
        return {
            "tests": [{"name": "test_placeholder", "code": f"def test_task_name():\n    assert '{task}'"}],
            "coverage_notes": raw.strip() or "Basic deterministic coverage scaffold.",
        }
