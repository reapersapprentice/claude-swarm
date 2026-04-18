"""Deterministic prompt assembly from symbolic schemas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

try:  # pragma: no cover - optional at runtime
    import tiktoken
except Exception:  # pragma: no cover - fallback when dependency unavailable
    tiktoken = None


@dataclass(frozen=True)
class PromptBuildResult:
    """Built prompt pair and token estimate."""

    system_prompt: str
    user_prompt: str
    token_estimate: int


class PromptBuilder:
    """Build deterministic prompts from template/ruleset/role definitions."""

    def __init__(self, schema_path: str = "configs/prompt_schema.yaml", encoding_name: str = "cl100k_base") -> None:
        self.schema_path = Path(schema_path)
        self.encoding_name = encoding_name
        self.schema = self._load_schema(self.schema_path)

    def _load_schema(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"rulesets": {}, "templates": {}, "role_blocks": {}}
        parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        parsed.setdefault("rulesets", {})
        parsed.setdefault("templates", {})
        parsed.setdefault("role_blocks", {})
        return parsed

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count with tiktoken when available."""
        if not text.strip():
            return 0
        if tiktoken is not None:
            encoding = tiktoken.get_encoding(self.encoding_name)
            return len(encoding.encode(text))
        return int(len(text.split()) * 1.3) + 1

    def build(
        self,
        template_key: str,
        role_key: str,
        task: str,
        context: str = "",
        ruleset_keys: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PromptBuildResult:
        """Build prompt strings from symbolic schema keys."""
        template = str(self.schema["templates"].get(template_key, "{task}\n\n{context}"))
        role_block = str(self.schema["role_blocks"].get(role_key, ""))

        rule_lines: List[str] = []
        selected_rules = list(ruleset_keys or ["T1", "T3", "T5"])
        for rule_key in selected_rules:
            rule = self.schema["rulesets"].get(rule_key)
            if rule:
                rule_lines.append(f"- {rule_key}: {rule}")

        user_prompt = template.format(task=task, context=context or "", metadata=metadata or {})
        parts = [part.strip() for part in [role_block.strip(), "Rules:\n" + "\n".join(rule_lines) if rule_lines else ""] if part.strip()]
        system_prompt = "\n\n".join(parts)

        token_estimate = self.estimate_tokens(f"{system_prompt}\n\n{user_prompt}")
        return PromptBuildResult(system_prompt=system_prompt, user_prompt=user_prompt, token_estimate=token_estimate)
