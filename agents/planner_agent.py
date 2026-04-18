"""Planner agent that decomposes work into node graph JSON."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .base_agent import AgentResult, BaseAgent


class PlannerAgent(BaseAgent):
    """Produce deterministic task graph plans."""

    def run(self, task: str, context: str = "") -> AgentResult:
        """Return plan as list of node objects with dependencies."""
        cached = self._check_cache(task, context)
        if cached:
            return cached

        raw = self.call_model(task, context)
        data = self._parse_or_fallback(raw, task)
        result = AgentResult(data=data, raw_output=json.dumps(data), tokens_used=self._estimate_tokens(task, context, raw))
        self._cache_result(task, context, result)
        return result

    def _parse_or_fallback(self, raw: str, task: str) -> List[Dict[str, Any]]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "nodes" in parsed:
                parsed = parsed["nodes"]
            if isinstance(parsed, list):
                for node in parsed:
                    if not all(key in node for key in ("id", "agent", "task")):
                        raise ValueError("Invalid planner node")
                    node.setdefault("dependencies", [])
                return parsed
        except Exception:
            pass

        return [
            {"id": "research", "agent": "researcher", "task": f"Research requirements for: {task}", "dependencies": []},
            {"id": "code", "agent": "coder", "task": f"Implement solution for: {task}", "dependencies": ["research"]},
            {"id": "review", "agent": "reviewer", "task": "Review implementation", "dependencies": ["code"]},
            {"id": "test", "agent": "tester", "task": "Create and run test strategy", "dependencies": ["review"]},
            {"id": "summary", "agent": "summarizer", "task": "Summarize final outputs", "dependencies": ["test"]},
        ]
