"""OpenAI model adapter with retry and budget enforcement."""

from __future__ import annotations

import os
import time
from typing import Optional

from token_infra.token_budget import TokenBudget

try:  # pragma: no cover - optional runtime dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - optional runtime dependency
    OpenAI = None


class OpenAIAdapter:
    """OpenAI adapter implementing claude-swarm model protocol."""

    def __init__(
        self,
        model: str = "gpt-4.1",
        api_key: Optional[str] = None,
        token_budget: Optional[TokenBudget] = None,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.5,
    ) -> None:
        self.model = model
        self.token_budget = token_budget
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        if OpenAI is None:
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
        if self.token_budget is not None:
            self.token_budget.validate_prompt(f"{system_prompt}\n\n{user_prompt}")
            max_tokens = min(max_tokens, self.token_budget.response_limit)

        if self.client is None:
            raise RuntimeError("openai package not installed; install optional dependency to use OpenAIAdapter")

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
                return response.output_text
            except Exception as exc:  # pragma: no cover - network behavior
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_delay_seconds * (attempt + 1))
        raise RuntimeError(f"OpenAI request failed after retries: {last_error}")
