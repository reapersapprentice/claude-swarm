"""Token budget policies and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml


class TokenBudgetError(ValueError):
    """Raised when token budgets are exceeded."""


@dataclass(frozen=True)
class BudgetProfile:
    """Named budget profile values."""

    prompt_limit: int
    response_limit: int
    soft_ratio: float


class TokenBudget:
    """Validate prompt usage against configured token budgets."""

    def __init__(
        self,
        prompt_limit: int,
        response_limit: int,
        soft_ratio: float = 0.85,
        estimator: Optional[Callable[[str], int]] = None,
    ) -> None:
        self.prompt_limit = int(prompt_limit)
        self.response_limit = int(response_limit)
        self.soft_ratio = float(soft_ratio)
        self.estimator = estimator or self._default_estimator

    @classmethod
    def from_profile(
        cls,
        profile: str,
        budgets_path: str = "configs/budgets.yaml",
        estimator: Optional[Callable[[str], int]] = None,
    ) -> "TokenBudget":
        data = yaml.safe_load(Path(budgets_path).read_text(encoding="utf-8")) if Path(budgets_path).exists() else {}
        raw: Dict[str, Any] = data.get(profile, {})
        if not raw:
            raise TokenBudgetError(f"Unknown budget profile: {profile}")
        return cls(
            prompt_limit=int(raw.get("prompt_limit", raw.get("max_prompt_tokens", 2000))),
            response_limit=int(raw.get("response_limit", raw.get("max_response_tokens", 1500))),
            soft_ratio=float(raw.get("soft_ratio", raw.get("utilization", 0.85))),
            estimator=estimator,
        )

    def _default_estimator(self, text: str) -> int:
        return int(len(text.split()) * 1.3) + 1 if text.strip() else 0

    def validate_prompt(self, prompt: str) -> int:
        """Validate prompt token usage and return estimated tokens."""
        tokens = int(self.estimator(prompt))
        if tokens > self.prompt_limit:
            raise TokenBudgetError(f"Prompt budget exceeded ({tokens}>{self.prompt_limit})")
        return tokens

    def remaining_prompt(self, prompt: str = "") -> int:
        """Return remaining prompt budget after accounting for prompt text."""
        used = int(self.estimator(prompt)) if prompt else 0
        remaining = self.prompt_limit - used
        return remaining if remaining > 0 else 0
