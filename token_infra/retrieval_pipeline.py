"""Context retrieval and prompt injection pipeline."""

from __future__ import annotations

from typing import Optional, Union

from .prompt_builder import PromptBuildResult, PromptBuilder
from .vector_store import VectorStore


class RetrievalPipeline:
    """Fetch relevant context from vector store and inject into prompts."""

    def __init__(self, store: VectorStore, builder: Optional[PromptBuilder] = None, max_results: int = 3) -> None:
        self.store = store
        self.builder = builder
        self.max_results = max_results

    def retrieve_context(self, query: str, top_k: Optional[int] = None) -> str:
        """Retrieve and format context snippets."""
        matches = self.store.query(query, top_k=top_k or self.max_results)
        if not matches:
            return ""
        lines = ["Retrieved context:"]
        for row in matches:
            lines.append(f"- [{row['key']}] {row['text']}")
        return "\n".join(lines)

    def inject_into_prompt(
        self,
        task: str,
        context: str,
        template_key: Optional[str] = None,
        role_key: Optional[str] = None,
    ) -> Union[str, PromptBuildResult]:
        """Inject retrieved context into context string or directly into built prompt."""
        retrieved = self.retrieve_context(task)
        merged = "\n\n".join(part for part in [context.strip(), retrieved.strip()] if part.strip())
        if self.builder is not None and template_key and role_key:
            return self.builder.build(template_key=template_key, role_key=role_key, task=task, context=merged)
        return merged

    def inject_context(self, task: str, context: str) -> str:
        """Inject retrieved context and always return a plain string."""
        retrieved = self.retrieve_context(task)
        return "\n\n".join(part for part in [context.strip(), retrieved.strip()] if part.strip())
