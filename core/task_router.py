"""Task router for planner outputs and routing-rule validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .execution_graph import ExecutionGraph, Node


class TaskRouter:
    """Build execution graphs from planner output using routing rules."""

    def __init__(self, routing_rules_path: str = "configs/routing_rules.yaml") -> None:
        self.routing_rules_path = Path(routing_rules_path)
        self.routing_rules = self._load_rules()

    def build_graph(self, planner_output: Any, capability_map: Optional[Dict[str, List[str]]] = None) -> ExecutionGraph:
        """Parse planner output and return an execution graph."""
        entries = self.parse_plan(planner_output)
        graph = ExecutionGraph()

        for entry in entries:
            node = Node(
                id=str(entry["id"]),
                agent=self.route_agent(entry.get("agent", ""), entry["task"]),
                task=entry["task"],
                dependencies=[str(dep) for dep in entry.get("dependencies", [])],
                optional=bool(entry.get("optional", False)),
            )
            self._validate_assignment(node.agent, node.task, capability_map or {})
            graph.add_node(node)

        for node in list(graph.nodes.values()):
            for dependency in node.dependencies:
                graph.add_dependency(node.id, dependency)

        return graph

    def parse_plan(self, planner_output: Any) -> List[Dict[str, Any]]:
        """Normalize planner output into a list of node dictionaries."""
        if isinstance(planner_output, str):
            planner_output = planner_output.strip()
            parsed = json.loads(planner_output)
        else:
            parsed = planner_output

        if isinstance(parsed, dict) and "nodes" in parsed:
            parsed = parsed["nodes"]
        if not isinstance(parsed, list):
            raise ValueError("Planner output must be a list of node definitions")

        normalized: List[Dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                raise ValueError("Planner node must be an object")
            if "id" not in item or "task" not in item:
                raise ValueError("Planner node must include 'id' and 'task'")
            normalized.append(item)
        return normalized

    def route_agent(self, requested_agent: str, task: str) -> str:
        """Route task to requested or inferred agent from keyword rules."""
        if requested_agent:
            return requested_agent

        task_l = task.lower()
        conditional_rules = self.routing_rules.get("conditional", [])
        for rule in conditional_rules:
            keyword = str(rule.get("keyword", "")).lower()
            if keyword and keyword in task_l:
                return str(rule["agent"])

        default = self.routing_rules.get("default_agent", "researcher")
        return str(default)

    def apply_conditionals(self, graph: ExecutionGraph, findings_text: str) -> None:
        """Apply conditional skip rules based on findings text."""
        rules = self.routing_rules.get("skip_if_contains", {})
        findings_l = findings_text.lower()
        for node_id, marker in rules.items():
            if marker.lower() in findings_l and node_id in graph.nodes:
                graph.nodes[node_id].optional = True

    def _validate_assignment(self, agent: str, task: str, capability_map: Dict[str, List[str]]) -> None:
        if agent not in capability_map:
            return
        capabilities = [cap.lower() for cap in capability_map[agent]]
        task_l = task.lower()
        if capabilities and not any(cap in task_l for cap in capabilities):
            raise ValueError(f"Task '{task}' is not compatible with agent '{agent}' capabilities")

    def _load_rules(self) -> Dict[str, Any]:
        if not self.routing_rules_path.exists():
            return {}
        return yaml.safe_load(self.routing_rules_path.read_text(encoding="utf-8")) or {}
