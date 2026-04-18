"""Execution graph primitives for task orchestration."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class NodeState(str, Enum):
    """Lifecycle states for graph nodes."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class Node:
    """A single executable task within an execution graph."""

    id: str
    agent: str
    task: str
    dependencies: List[str] = field(default_factory=list)
    optional: bool = False
    state: NodeState = NodeState.PENDING
    result: Optional[str] = None


class ExecutionGraph:
    """Directed acyclic graph of task nodes."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        if node.id in self.nodes:
            raise ValueError(f"Node '{node.id}' already exists")
        self.nodes[node.id] = node

    def add_dependency(self, node_id: str, depends_on_id: str) -> None:
        """Add a dependency edge between two nodes."""
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' not found")
        if depends_on_id not in self.nodes:
            raise KeyError(f"Dependency node '{depends_on_id}' not found")
        if depends_on_id not in self.nodes[node_id].dependencies:
            self.nodes[node_id].dependencies.append(depends_on_id)

    def detect_cycles(self) -> bool:
        """Return True if a cycle exists in the graph."""
        indegree = {node_id: 0 for node_id in self.nodes}
        for node in self.nodes.values():
            for dep in node.dependencies:
                indegree[node.id] += 1

        queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
        visited = 0
        adjacency = self._adjacency()
        while queue:
            current = queue.popleft()
            visited += 1
            for child in adjacency[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        return visited != len(self.nodes)

    def topological_sort(self) -> List[str]:
        """Return node ids in topological order."""
        if self.detect_cycles():
            raise ValueError("Execution graph contains cycle")

        indegree = {node_id: 0 for node_id in self.nodes}
        adjacency = self._adjacency()
        for node in self.nodes.values():
            for dep in node.dependencies:
                indegree[node.id] += 1

        queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
        ordered: List[str] = []
        while queue:
            current = queue.popleft()
            ordered.append(current)
            for child in sorted(adjacency[current]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        return ordered

    def get_parallel_groups(self) -> List[List[str]]:
        """Return executable batches where each batch can run in parallel."""
        if self.detect_cycles():
            raise ValueError("Execution graph contains cycle")

        indegree = {node_id: 0 for node_id in self.nodes}
        adjacency = self._adjacency()
        for node in self.nodes.values():
            for dep in node.dependencies:
                indegree[node.id] += 1

        groups: List[List[str]] = []
        ready = sorted([node_id for node_id, degree in indegree.items() if degree == 0])
        while ready:
            groups.append(ready)
            next_ready: Set[str] = set()
            for node_id in ready:
                for child in adjacency[node_id]:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        next_ready.add(child)
            ready = sorted(next_ready)
        return groups

    def visualize(self) -> str:
        """Render graph as compact ASCII text."""
        lines: List[str] = []
        for node_id in self.topological_sort():
            node = self.nodes[node_id]
            if node.dependencies:
                deps = ", ".join(node.dependencies)
                lines.append(f"{node_id} [{node.agent}] <- {deps}")
            else:
                lines.append(f"{node_id} [{node.agent}] <- ROOT")
        return "\n".join(lines)

    def _adjacency(self) -> Dict[str, List[str]]:
        adjacency: Dict[str, List[str]] = defaultdict(list)
        for node in self.nodes.values():
            for dep in node.dependencies:
                adjacency[dep].append(node.id)
        return adjacency
