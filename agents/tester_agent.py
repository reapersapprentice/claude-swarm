"""Tester agent implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .base_agent import AgentResult, BaseAgent, ModelInterface
from token_infra.prompt_builder import PromptBuilder
from token_infra.token_budget import TokenBudget


class TesterAgent(BaseAgent):
    """Generate structured tests and coverage notes."""

    DEFAULT_TEMPLATE_KEY = "TMP:TEST_GEN"
    DEFAULT_ROLE_KEY = "ROLE_TESTER"
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
