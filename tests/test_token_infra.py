"""Tests for token infrastructure integration."""

from __future__ import annotations

import json

from agents.base_agent import ModelInterface
from pipelines import build_code_pipeline
from token_infra.prompt_builder import PromptBuilder
from token_infra.retrieval_pipeline import RetrievalPipeline
from token_infra.token_budget import TokenBudget, TokenBudgetError
from token_infra.vector_store import VectorStore


class MiniIntegrationModel(ModelInterface):
    """Small deterministic model for token infra integration tests."""

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
        if "Decompose into atomic execution nodes" in user_prompt:
            return json.dumps(
                [
                    {"id": "plan", "agent": "planner", "task": "Decompose plan for feature", "dependencies": []},
                    {"id": "code", "agent": "coder", "task": "Implement feature", "dependencies": ["plan"]},
                ]
            )
        if '"files"' in user_prompt:
            return json.dumps(
                {
                    "files": [{"path": "main.py", "content": "print('ok')"}],
                    "explanation": "implemented",
                }
            )
        return json.dumps({"summary": "ok"})


def test_prompt_builder_swarm_template_builds() -> None:
    builder = PromptBuilder(schema_path="configs/prompt_schema.yaml")
    built = builder.build(
        template_key="TMP:PLAN",
        role_key="ROLE_PLANNER",
        task="Build an execution graph",
        context="Existing repo context",
    )
    assert "Decompose into atomic execution nodes" in built.user_prompt
    assert "planning specialist" in built.system_prompt.lower()
    assert built.token_estimate > 0


def test_token_budget_enforces_limits() -> None:
    budget = TokenBudget(prompt_limit=10, response_limit=8)
    budget.validate_prompt("short prompt")
    raised = False
    try:
        budget.validate_prompt(" ".join(["long"] * 100))
    except TokenBudgetError:
        raised = True
    assert raised is True
    assert budget.remaining_prompt("short prompt") <= budget.prompt_limit


def test_vector_store_fallback_without_chromadb() -> None:
    store = VectorStore(prefer_chromadb=False)
    store.add_document("n1", "alpha beta gamma")
    store.add_document("n2", "delta epsilon")
    matches = store.query("alpha", top_k=1)
    assert store.backend == "fallback"
    assert matches[0]["key"] == "n1"


def test_retrieval_pipeline_injects_context_into_prompt_builder() -> None:
    store = VectorStore(prefer_chromadb=False)
    store.add_document("research", "Important implementation context")
    builder = PromptBuilder(schema_path="configs/prompt_schema.yaml")
    pipeline = RetrievalPipeline(store=store, builder=builder)
    built = pipeline.inject_into_prompt(
        task="Implement feature",
        context="Base context",
        template_key="TMP:CODE_GEN",
        role_key="ROLE_CODER",
    )
    assert "Retrieved context" in built.user_prompt
    assert "Important implementation context" in built.user_prompt


def test_mini_pipeline_planner_to_coder_with_token_infra() -> None:
    controller = build_code_pipeline(
        model=MiniIntegrationModel(),
        token_config={
            "prompt_schema_path": "configs/prompt_schema.yaml",
            "budgets_path": "configs/budgets.yaml",
            "prefer_chromadb": False,
            "retrieval_top_k": 2,
        },
    )
    result = controller.execute("implement small feature")
    assert result.success is True
    assert "code" in result.node_results
    matches = controller.vector_store.query("Implement feature", top_k=1)
    assert matches
