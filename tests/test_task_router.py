"""Tests for task router."""

import json

from core.task_router import TaskRouter


def test_build_graph_and_validate_capabilities() -> None:
    router = TaskRouter("configs/routing_rules.yaml")
    plan = json.dumps([
        {"id": "a", "agent": "researcher", "task": "research api", "dependencies": []},
        {"id": "b", "agent": "coder", "task": "implement api", "dependencies": ["a"]},
    ])
    graph = router.build_graph(plan, capability_map={"researcher": ["research"], "coder": ["implement"]})
    assert set(graph.nodes.keys()) == {"a", "b"}


def test_conditional_routing_without_agent() -> None:
    router = TaskRouter("configs/routing_rules.yaml")
    agent = router.route_agent("", "Implement API endpoint")
    assert agent == "coder"
