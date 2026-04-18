"""Tests for execution graph behavior."""

from core.execution_graph import ExecutionGraph, Node


def test_topological_sort_and_parallel_groups() -> None:
    graph = ExecutionGraph()
    graph.add_node(Node(id="a", agent="planner", task="A"))
    graph.add_node(Node(id="b", agent="coder", task="B", dependencies=["a"]))
    graph.add_node(Node(id="c", agent="tester", task="C", dependencies=["a"]))
    graph.add_node(Node(id="d", agent="reviewer", task="D", dependencies=["b", "c"]))

    assert graph.topological_sort()[0] == "a"
    assert graph.get_parallel_groups() == [["a"], ["b", "c"], ["d"]]


def test_cycle_detection() -> None:
    graph = ExecutionGraph()
    graph.add_node(Node(id="a", agent="planner", task="A", dependencies=["b"]))
    graph.add_node(Node(id="b", agent="coder", task="B", dependencies=["a"]))
    assert graph.detect_cycles() is True
