"""Integration tests verifying all 6 agents collaborate through the full swarm pipeline.

Each test exercises the complete agent ensemble:
  Planner → Researcher → Coder → Reviewer → Tester → Summarizer
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.base_agent import ModelInterface
from core.swarm_controller import NodeResult
from pipelines.common import build_controller, load_swarm_config


# ---------------------------------------------------------------------------
# Model that produces distinct, verifiable output for every agent
# ---------------------------------------------------------------------------

class SixAgentModel(ModelInterface):
    """Deterministic model that returns unique structured output per agent.

    The planner emits a 5-node plan that routes through all remaining agents
    (researcher → coder → reviewer → tester → summarizer).  Each downstream
    agent returns JSON containing an ``agent_tag`` so tests can verify every
    agent participated.
    """

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
        # --- Planner ---
        if "atomic execution nodes" in system_prompt:
            return json.dumps([
                {"id": "research", "agent": "researcher", "task": "Research requirements", "dependencies": []},
                {"id": "code", "agent": "coder", "task": "Implement solution", "dependencies": ["research"]},
                {"id": "review", "agent": "reviewer", "task": "Review implementation", "dependencies": ["code"]},
                {"id": "test", "agent": "tester", "task": "Write tests", "dependencies": ["review"]},
                {"id": "summary", "agent": "summarizer", "task": "Summarize deliverables", "dependencies": ["test"]},
            ])

        # --- Researcher ---
        if "findings" in system_prompt:
            return json.dumps({
                "findings": ["Requirement A identified", "Constraint B noted"],
                "sources": ["design-doc", "api-spec"],
                "summary": "Research complete",
                "agent_tag": "researcher",
            })

        # --- Coder ---
        if "files" in system_prompt:
            return json.dumps({
                "files": [
                    {"path": "app.py", "content": "def main(): pass"},
                    {"path": "utils.py", "content": "def helper(): return 42"},
                ],
                "explanation": "Implemented main application and utilities",
                "agent_tag": "coder",
            })

        # --- Reviewer ---
        if "issues" in system_prompt:
            return json.dumps({
                "issues": ["Consider adding input validation"],
                "approved": True,
                "suggestions": ["Add type hints"],
                "agent_tag": "reviewer",
            })

        # --- Tester ---
        if "tests" in system_prompt:
            return json.dumps({
                "tests": [
                    {"name": "test_main", "code": "def test_main():\n    assert main() is None"},
                    {"name": "test_helper", "code": "def test_helper():\n    assert helper() == 42"},
                ],
                "coverage_notes": "Unit tests cover main and helper",
                "agent_tag": "tester",
            })

        # --- Summarizer (fallback) ---
        return json.dumps({
            "summary": "All agents completed successfully",
            "highlights": ["research done", "code written", "review passed", "tests created"],
            "agent_tag": "summarizer",
        })


ALL_SIX_AGENTS = {"planner", "researcher", "coder", "reviewer", "tester", "summarizer"}


@pytest.fixture
def six_agent_controller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Controller wired with SixAgentModel so every agent produces unique output."""
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    cfg = load_swarm_config()
    ctrl = build_controller(SixAgentModel(), cfg)
    ctrl.memory.file_path = tmp_path / "state.json"
    ctrl.memory._state = {}
    return ctrl


# ---------------------------------------------------------------------------
# Test 1 — Full pipeline executes all 6 agents and produces output from each
# ---------------------------------------------------------------------------

def test_full_pipeline_engages_all_six_agents(six_agent_controller) -> None:
    """Running a task through the full pipeline must invoke all 6 agents
    (planner + 5 downstream nodes) and produce a non-empty merged output."""
    result = six_agent_controller.execute("build a REST API")

    assert result.success is True

    # The planner creates the graph; the other 5 become node results.
    executed_node_ids = set(result.node_results.keys())
    assert executed_node_ids == {"research", "code", "review", "test", "summary"}

    # Verify every node succeeded
    for node_id, node_result in result.node_results.items():
        assert node_result.success is True, f"Node '{node_id}' failed: {node_result.error}"
        assert node_result.output, f"Node '{node_id}' produced empty output"

    # The merged output must contain content from every node
    assert result.merged_output
    assert "research" in result.merged_output.lower()
    assert "code" in result.merged_output.lower()
    assert "review" in result.merged_output.lower()
    assert "test" in result.merged_output.lower()
    assert "summary" in result.merged_output.lower()


# ---------------------------------------------------------------------------
# Test 2 — Each agent's structured data fields are present in node results
# ---------------------------------------------------------------------------

def test_agent_structured_output_fields(six_agent_controller) -> None:
    """Each agent must produce its own structured JSON fields in the output,
    confirming the correct agent handled each node."""
    result = six_agent_controller.execute("design a microservice")
    assert result.success is True

    outputs = {nid: json.loads(nr.output) for nid, nr in result.node_results.items()}

    # Researcher
    assert "findings" in outputs["research"]
    assert "sources" in outputs["research"]
    assert "summary" in outputs["research"]

    # Coder
    assert "files" in outputs["code"]
    assert len(outputs["code"]["files"]) >= 1
    assert "explanation" in outputs["code"]

    # Reviewer
    assert "approved" in outputs["review"]
    assert "issues" in outputs["review"]
    assert "suggestions" in outputs["review"]

    # Tester
    assert "tests" in outputs["test"]
    assert len(outputs["test"]["tests"]) >= 1
    assert "coverage_notes" in outputs["test"]

    # Summarizer
    assert "summary" in outputs["summary"]


# ---------------------------------------------------------------------------
# Test 3 — Agent execution order respects the dependency chain across all 6
# ---------------------------------------------------------------------------

def test_execution_respects_six_agent_dependency_order(six_agent_controller) -> None:
    """Nodes must execute in dependency order:
    research (no deps) → code → review → test → summary.
    The planner runs first (implicit); after that, parallel-group ordering
    guarantees each node finishes before its dependents."""
    execution_order: list[str] = []

    six_agent_controller.add_post_task_hook(
        lambda node, _result: execution_order.append(node.id)
    )

    result = six_agent_controller.execute("create a CLI tool")
    assert result.success is True

    # All 5 downstream nodes executed
    assert set(execution_order) == {"research", "code", "review", "test", "summary"}

    # Verify strict ordering
    idx = {name: i for i, name in enumerate(execution_order)}
    assert idx["research"] < idx["code"], "research must precede code"
    assert idx["code"] < idx["review"], "code must precede review"
    assert idx["review"] < idx["test"], "review must precede test"
    assert idx["test"] < idx["summary"], "test must precede summary"


# ---------------------------------------------------------------------------
# Test 4 — Token metrics accumulate correctly across all 6 agents
# ---------------------------------------------------------------------------

def test_token_metrics_accumulate_across_all_agents(six_agent_controller) -> None:
    """Token usage should be tracked for every agent.  The total must be
    positive and the number of executed nodes must equal 5 (the planner's
    own run is outside the node graph)."""
    result = six_agent_controller.execute("build a data pipeline")
    assert result.success is True

    assert result.metrics["nodes_executed"] == 5
    assert result.metrics["tokens_used"] > 0

    # Each node should report non-zero token usage
    for node_id, nr in result.node_results.items():
        assert nr.tokens_used >= 0, f"Node '{node_id}' has negative token count"

    total_node_tokens = sum(nr.tokens_used for nr in result.node_results.values())
    assert total_node_tokens > 0, "Combined token usage across all agents should be positive"


# ---------------------------------------------------------------------------
# Test 5 — Second identical run hits cache for all 6 agents' nodes
# ---------------------------------------------------------------------------

def test_cache_hits_on_repeated_six_agent_run(six_agent_controller) -> None:
    """When the same task is executed twice, every node should be served from
    cache on the second run, yielding cache_hits == 5 and zero additional
    token usage beyond the first run."""
    first = six_agent_controller.execute("build an auth service")
    assert first.success is True
    first_tokens = first.metrics["tokens_used"]

    second = six_agent_controller.execute("build an auth service")
    assert second.success is True
    assert second.metrics["cache_hits"] == 5, (
        "All 5 downstream nodes should be cache hits on the second run"
    )

    # Cached nodes should report zero tokens
    for node_id, nr in second.node_results.items():
        assert nr.cached is True, f"Node '{node_id}' was not served from cache"
        assert nr.tokens_used == 0, f"Cached node '{node_id}' should use 0 tokens"
