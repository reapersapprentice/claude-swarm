"""Tests for error handling and hook/caching paths in SwarmController."""

from __future__ import annotations

from core.execution_graph import Node
from core.swarm_controller import NodeResult


def test_pre_task_hook_called(controller):
    """Pre-task hook is invoked at least once during execution."""
    calls = []
    controller.add_pre_task_hook(lambda node, ctx: calls.append((node, ctx)))
    controller.execute("Build a calculator app")
    assert len(calls) >= 1


def test_post_task_hook_called(controller):
    """Post-task hook is invoked at least once during execution."""
    calls = []
    controller.add_post_task_hook(lambda node, result: calls.append((node, result)))
    controller.execute("Build a calculator app")
    assert len(calls) >= 1


def test_hooks_receive_correct_types(controller):
    """Pre-task hook receives (Node, dict), post-task hook receives (Node, NodeResult)."""
    pre_calls = []
    post_calls = []
    controller.add_pre_task_hook(lambda node, ctx: pre_calls.append((node, ctx)))
    controller.add_post_task_hook(lambda node, result: post_calls.append((node, result)))

    controller.execute("Build a calculator app")

    for node, ctx in pre_calls:
        assert isinstance(node, Node)
        assert isinstance(ctx, dict)

    for node, result in post_calls:
        assert isinstance(node, Node)
        assert isinstance(result, NodeResult)


def test_result_caching(controller):
    """Running the same task twice produces cache hits on the second run."""
    controller.execute("Build a calculator app")
    second = controller.execute("Build a calculator app")
    assert second.metrics["cache_hits"] > 0


def test_dry_run_returns_graph_visualization(controller):
    """Dry run produces a non-empty graph_visualization."""
    result = controller.execute("Build a calculator app", dry_run=True)
    assert result.graph_visualization
    assert isinstance(result.graph_visualization, str)
