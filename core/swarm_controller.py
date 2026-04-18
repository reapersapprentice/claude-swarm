"""Swarm controller responsible for orchestrating graph-based agent execution."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from token_infra.compression import CompressionPipeline
from token_infra.retrieval_pipeline import RetrievalPipeline
from token_infra.vector_store import VectorStore

from .execution_graph import ExecutionGraph, Node, NodeState


@dataclass
class NodeResult:
    """Result of an executed node."""

    node_id: str
    output: str
    tokens_used: int = 0
    cached: bool = False
    success: bool = True
    error: Optional[str] = None


@dataclass
class SwarmResult:
    """Aggregated swarm execution result."""

    success: bool
    merged_output: str
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    graph_visualization: str = ""


class SwarmController:
    """Central orchestrator for agent execution across a DAG."""

    def __init__(
        self,
        registry: Any,
        router: Any,
        memory: Any,
        optimizer: Any,
        config: Optional[Dict[str, Any]] = None,
        vector_store: Optional[VectorStore] = None,
        retrieval_pipeline: Optional[RetrievalPipeline] = None,
        compression_pipeline: Optional[CompressionPipeline] = None,
    ) -> None:
        self.registry = registry
        self.router = router
        self.memory = memory
        self.optimizer = optimizer
        self.config = config or {}
        self.vector_store = vector_store
        self.retrieval_pipeline = retrieval_pipeline
        self.compression_pipeline = compression_pipeline
        self.pre_task_hooks: List[Callable[[Node, Dict[str, str]], None]] = []
        self.post_task_hooks: List[Callable[[Node, NodeResult], None]] = []

    def add_pre_task_hook(self, callback: Callable[[Node, Dict[str, str]], None]) -> None:
        """Register callback executed before each node run."""
        self.pre_task_hooks.append(callback)

    def add_post_task_hook(self, callback: Callable[[Node, NodeResult], None]) -> None:
        """Register callback executed after each node run."""
        self.post_task_hooks.append(callback)

    def execute(self, task: str, dry_run: bool = False) -> SwarmResult:
        """Run the full swarm pipeline from planning through merge."""
        started = time.perf_counter()
        planner = self.registry.get("planner")
        plan_result = planner.run(task, context="")
        capability_map = {name: self.registry.capabilities(name) for name in self.registry.list_agents()}
        graph: ExecutionGraph = self.router.build_graph(plan_result.data if hasattr(plan_result, "data") else plan_result,
                                                        capability_map=capability_map)

        if dry_run:
            return SwarmResult(
                success=True,
                merged_output="",
                node_results={},
                metrics={"dry_run": True, "duration_seconds": time.perf_counter() - started},
                graph_visualization=graph.visualize(),
            )

        node_results: Dict[str, NodeResult] = {}
        retries_enabled = bool(self.config.get("retry_failed_nodes", True))
        max_retries = int(self.config.get("max_retries", 2))

        for group in graph.get_parallel_groups():
            for node_id in group:
                node = graph.nodes[node_id]
                failed_dependencies = [dep for dep in node.dependencies if graph.nodes[dep].state in {NodeState.FAILED, NodeState.SKIPPED}]
                if failed_dependencies and node.optional:
                    node.state = NodeState.SKIPPED
                    node_results[node.id] = NodeResult(node_id=node.id, output="", success=False, error="Skipped due to failed dependencies")
                    continue

                attempts = 0
                last_result: Optional[NodeResult] = None
                while attempts <= max_retries:
                    attempts += 1
                    result = self.execute_node(node, {dep: graph.nodes[dep].result or "" for dep in node.dependencies})
                    last_result = result
                    if result.success:
                        break
                    if not retries_enabled:
                        break
                assert last_result is not None
                node_results[node.id] = last_result
                if not last_result.success and not node.optional:
                    break
            if any(not result.success and not graph.nodes[node_id].optional for node_id, result in node_results.items() if node_id in group):
                break

        merged_output = self.merge_results({node_id: result.output for node_id, result in node_results.items() if result.success})
        duration = time.perf_counter() - started
        success = all(result.success or graph.nodes[node_id].optional for node_id, result in node_results.items())
        metrics = {
            "tokens_used": self.optimizer.tokens_used,
            "duration_seconds": duration,
            "cache_hits": sum(1 for res in node_results.values() if res.cached),
            "nodes_executed": len(node_results),
        }
        return SwarmResult(
            success=success,
            merged_output=merged_output,
            node_results=node_results,
            metrics=metrics,
            graph_visualization=graph.visualize(),
        )

    def execute_node(self, node: Node, context: Dict[str, str]) -> NodeResult:
        """Execute one node with compression, cache, and hooks."""
        node.state = NodeState.RUNNING
        for hook in self.pre_task_hooks:
            hook(node, context)

        agent = self.registry.get(node.agent)
        context_text = "\n\n".join(value for value in context.values() if value)
        if self.retrieval_pipeline and self.vector_store:
            context_text = self.retrieval_pipeline.inject_context(node.task, context_text)
        optimized = self.optimizer.compress(context_text, task=node.task, agent_name=node.agent)

        cached = self.memory.get("results", f"{node.agent}:{node.task}:{optimized}")
        if cached is not None:
            node.state = NodeState.COMPLETED
            node.result = str(cached)
            if self.vector_store is not None:
                self.vector_store.add_document(node.id, node.result, metadata={"agent": node.agent, "task": node.task})
            result = NodeResult(node_id=node.id, output=node.result, cached=True, tokens_used=0)
            for hook in self.post_task_hooks:
                hook(node, result)
            return result

        try:
            response = agent.run(node.task, optimized)
            output = str(response.raw_output if hasattr(response, "raw_output") else response)
            if self.compression_pipeline is not None:
                output = self.compression_pipeline.compress(output, task=node.task, max_tokens=getattr(agent, "token_budget", None))
            tokens_used = int(getattr(response, "tokens_used", self.optimizer.estimate_tokens(node.task + " " + optimized + " " + output)))
            self.optimizer.enforce_budget(tokens_used, getattr(agent, "token_budget", None))
            self.optimizer.record_usage(tokens_used)
            node.result = output
            node.state = NodeState.COMPLETED
            self.memory.set("results", f"{node.agent}:{node.task}:{optimized}", output)
            if self.vector_store is not None:
                self.vector_store.add_document(node.id, output, metadata={"agent": node.agent, "task": node.task})
            result = NodeResult(node_id=node.id, output=output, tokens_used=tokens_used)
        except Exception as exc:  # pragma: no cover - safety catch
            node.state = NodeState.FAILED
            result = NodeResult(node_id=node.id, output="", success=False, error=str(exc))

        for hook in self.post_task_hooks:
            hook(node, result)
        return result

    def merge_results(self, results: Dict[str, str]) -> str:
        """Merge node outputs into deterministic final string."""
        return "\n\n".join(f"[{node_id}]\n{results[node_id]}" for node_id in sorted(results))
