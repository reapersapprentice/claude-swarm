"""Base agent primitives and model interface abstraction."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from token_infra.prompt_builder import PromptBuilder
from token_infra.token_budget import TokenBudget


class ModelInterface(Protocol):
    """Protocol to integrate any model backend."""

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
        """Generate model output string for a given prompt pair."""


@dataclass
class AgentResult:
    """Structured result wrapper for all agent runs."""

    data: Dict[str, Any]
    raw_output: str
    tokens_used: int
    cached: bool = False


class BaseAgent(ABC):
    """Abstract base class for all swarm agents."""

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
        self.name = name
        self.prompt_path = prompt_path
        self.system_prompt = self._load_prompt(prompt_path)
        self.model = model
        self.token_budget = token_budget
        self.prompt_builder = prompt_builder
        self.token_budget_manager = token_budget_manager
        self.template_key = template_key
        self.role_key = role_key
        self._result_cache: Dict[str, AgentResult] = {}

    @abstractmethod
    def run(self, task: str, context: str = "") -> AgentResult:
        """Execute the agent task and return structured result."""

    def call_model(self, task: str, context: str = "") -> str:
        """Invoke model using deterministic prompt envelope."""
        system_prompt = self.system_prompt
        user_prompt = f"Task:\n{task}\n\nContext:\n{context}".strip()
        if self.prompt_builder and self.template_key and self.role_key:
            built_prompt = self.prompt_builder.build(
                template_key=self.template_key,
                role_key=self.role_key,
                task=task,
                context=context,
            )
            system_prompt = built_prompt.system_prompt or system_prompt
            user_prompt = built_prompt.user_prompt
            if self.token_budget_manager:
                self.token_budget_manager.validate_prompt(f"{system_prompt}\n\n{user_prompt}")
        elif self.token_budget_manager:
            self.token_budget_manager.validate_prompt(f"{system_prompt}\n\n{user_prompt}")
        return self.model.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=min(self.token_budget, self.token_budget_manager.response_limit)
            if self.token_budget_manager
            else self.token_budget,
            temperature=0.0,
        )

    def _load_prompt(self, path: str) -> str:
        """Load static system prompt from file path."""
        prompt_path = Path(path)
        return prompt_path.read_text(encoding="utf-8")

    def _check_cache(self, task: str, context: str) -> Optional[AgentResult]:
        """Return cached result if present for same task/context pair."""
        cache_key = self._cache_key(task, context)
        cached = self._result_cache.get(cache_key)
        if cached is None:
            return None
        return AgentResult(data=cached.data, raw_output=cached.raw_output, tokens_used=0, cached=True)

    def _cache_result(self, task: str, context: str, result: AgentResult) -> None:
        """Persist deterministic result in local cache."""
        self._result_cache[self._cache_key(task, context)] = result

    def _cache_key(self, task: str, context: str) -> str:
        seed = json.dumps({"task": task, "context": context}, sort_keys=True)
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def _estimate_tokens(self, *parts: str) -> int:
        text = " ".join(parts).strip()
        if not text:
            return 0
        return int(len(text.split()) * 1.3) + 1
