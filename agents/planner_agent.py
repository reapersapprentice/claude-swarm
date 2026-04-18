"""Planner agent that decomposes work into node graph JSON."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base_agent import AgentResult, BaseAgent
from .base_agent import ModelInterface
from token_infra.prompt_builder import PromptBuilder
from token_infra.token_budget import TokenBudget


class PlannerAgent(BaseAgent):
    """Produce deterministic task graph plans."""

    DEFAULT_TEMPLATE_KEY = "TMP:PLAN"
    DEFAULT_ROLE_KEY = "ROLE_PLANNER"
    DEFAULT_BUDGET_PROFILE = "standard"

    def __init__(
        self,
        name: str,
        prompt_path: str,
        model: ModelInterface,
        token_budget: int = 4000,
        prompt_builder: Optional[PromptBuilder] = None,
        token_budget_manager: Optional[TokenBudget] = None,
        template_key: Optional[str] = None,
        role_key: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            prompt_path=prompt_path,
            model=model,
            token_budget=token_budget,
            prompt_builder=prompt_builder,
            token_budget_manager=token_budget_manager,
            template_key=template_key or self.DEFAULT_TEMPLATE_KEY,
            role_key=role_key or self.DEFAULT_ROLE_KEY,
        )

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
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            pass

        return [
            {"id": "research", "agent": "researcher", "task": f"Research requirements for: {task}", "dependencies": []},
            {"id": "code", "agent": "coder", "task": f"Implement solution for: {task}", "dependencies": ["research"]},
            {"id": "review", "agent": "reviewer", "task": "Review implementation", "dependencies": ["code"]},
            {"id": "test", "agent": "tester", "task": "Create and run test strategy", "dependencies": ["review"]},
            {"id": "summary", "agent": "summarizer", "task": "Summarize final outputs", "dependencies": ["test"]},
        ]
