"""Anthropic Claude adapter with retry and budget enforcement."""

from __future__ import annotations

import os
import time
from typing import Optional

from token_infra.token_budget import TokenBudget

try:  # pragma: no cover - optional runtime dependency
    import anthropic
except Exception:  # pragma: no cover - optional runtime dependency
    anthropic = None


class ClaudeAdapter:
    """Claude adapter implementing claude-swarm model protocol."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        token_budget: Optional[TokenBudget] = None,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.5,
    ) -> None:
        self.model = model
        self.token_budget = token_budget
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        if anthropic is None:
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
        if self.token_budget is not None:
            self.token_budget.validate_prompt(f"{system_prompt}\n\n{user_prompt}")
            max_tokens = min(max_tokens, self.token_budget.response_limit)

        if self.client is None:
            raise RuntimeError("anthropic package not installed; install optional dependency to use ClaudeAdapter")

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                if not response.content:
                    return ""
                return "".join(part.text for part in response.content if getattr(part, "type", "") == "text")
            except Exception as exc:  # pragma: no cover - network behavior
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_delay_seconds * (attempt + 1))
        raise RuntimeError(f"Claude request failed after retries: {last_error}")
