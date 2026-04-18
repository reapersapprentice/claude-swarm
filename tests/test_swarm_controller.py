"""Tests for swarm controller execution and dry-run behavior."""

from core.state_store import StateStore


def test_execute_dry_run(controller) -> None:
    result = controller.execute("build feature", dry_run=True)
    assert result.success is True
    assert "research" in result.graph_visualization


def test_execute_pipeline_and_state_store(tmp_path) -> None:
    store = StateStore(file_path=str(tmp_path / "state.json"), default_ttl=1)
    store.set("ns", "k", {"x": 1})
    assert store.get("ns", "k") == {"x": 1}


def test_execute_full(controller) -> None:
    result = controller.execute("build feature", dry_run=False)
    assert result.success is True
    assert result.metrics["nodes_executed"] >= 1
    assert "summary" in result.merged_output.lower()
