"""Structured logger for swarm execution traces."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict


class StructuredLogger:
    """JSON logger with execution and token usage helpers."""

    def __init__(self, name: str = "claude_swam") -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

    def log(self, level: int, message: str, **fields: Any) -> None:
        """Emit structured log line."""
        payload: Dict[str, Any] = {"message": message, **fields}
        self._logger.log(level, json.dumps(payload, sort_keys=True))

    def trace_execution(self, node_id: str, state: str) -> None:
        """Log node execution state transition."""
        self.log(logging.INFO, "node_execution", node_id=node_id, state=state)

    def log_token_usage(self, agent: str, tokens: int) -> None:
        """Log token usage entry."""
        self.log(logging.INFO, "token_usage", agent=agent, tokens=tokens)
