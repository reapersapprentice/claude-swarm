"""Shared helpers for building configured controllers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from agents import CoderAgent, PlannerAgent, ResearcherAgent, ReviewerAgent, SummarizerAgent, TesterAgent
from agents.base_agent import ModelInterface
from core import AgentRegistry, StateStore, SwarmController, TaskRouter, TokenOptimizer


class EchoModel(ModelInterface):
    """Deterministic local model implementation for offline operation and tests."""

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
        if "atomic execution nodes" in system_prompt:
            return json.dumps([
                {"id": "research", "agent": "researcher", "task": "Research task", "dependencies": []},
                {"id": "code", "agent": "coder", "task": "Implement task", "dependencies": ["research"]},
                {"id": "summary", "agent": "summarizer", "task": "Summarize task", "dependencies": ["code"]},
            ])
        return json.dumps({"summary": user_prompt[:max_tokens]})


def load_swarm_config(path: str = "configs/swarm_config.yaml") -> Dict[str, Any]:
    """Load YAML swarm config from disk."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def build_registry(model: ModelInterface, limits: Dict[str, Any]) -> AgentRegistry:
    """Create registry and register default agent set."""
    prompt_dir = Path("prompts")
    registry = AgentRegistry()
    registry.auto_register_defaults(
        {
            "planner": {
                "factory": PlannerAgent,
                "config": {"name": "planner", "prompt_path": str(prompt_dir / "planner.md"), "model": model,
                           "token_budget": limits.get("planner", {}).get("max_tokens", 3000)},
                "capabilities": ["plan", "decompose", "route"],
            },
            "researcher": {
                "factory": ResearcherAgent,
                "config": {"name": "researcher", "prompt_path": str(prompt_dir / "researcher.md"), "model": model,
                           "token_budget": limits.get("researcher", {}).get("max_tokens", 5000)},
                "capabilities": ["research", "analyze", "investigate"],
            },
            "coder": {
                "factory": CoderAgent,
                "config": {"name": "coder", "prompt_path": str(prompt_dir / "coder.md"), "model": model,
                           "token_budget": limits.get("coder", {}).get("max_tokens", 7000)},
                "capabilities": ["code", "implement", "build"],
            },
            "reviewer": {
                "factory": ReviewerAgent,
                "config": {"name": "reviewer", "prompt_path": str(prompt_dir / "reviewer.md"), "model": model,
                           "token_budget": limits.get("reviewer", {}).get("max_tokens", 4000)},
                "capabilities": ["review", "validate", "audit"],
            },
            "tester": {
                "factory": TesterAgent,
                "config": {"name": "tester", "prompt_path": str(prompt_dir / "tester.md"), "model": model,
                           "token_budget": limits.get("tester", {}).get("max_tokens", 4500)},
                "capabilities": ["test", "verify", "coverage"],
            },
            "summarizer": {
                "factory": SummarizerAgent,
                "config": {"name": "summarizer", "prompt_path": str(prompt_dir / "summarizer.md"), "model": model,
                           "token_budget": limits.get("summarizer", {}).get("max_tokens", 3000)},
                "capabilities": ["summarize", "compress", "merge"],
            },
        }
    )
    return registry


def build_controller(model: ModelInterface, config: Dict[str, Any]) -> SwarmController:
    """Build fully configured SwarmController instance."""
    limits_path = Path("configs/agent_limits.yaml")
    limits = yaml.safe_load(limits_path.read_text(encoding="utf-8")) if limits_path.exists() else {}
    registry = build_registry(model, limits)
    optimizer = TokenOptimizer(
        {
            "max_tokens_per_agent": 4000,
            "max_total_tokens": config.get("swarm", {}).get("max_total_tokens", 50000),
            "compression_threshold": 1000,
        }
    )
    router = TaskRouter("configs/routing_rules.yaml")
    memory = StateStore()
    return SwarmController(
        registry=registry,
        router=router,
        memory=memory,
        optimizer=optimizer,
        config=config.get("swarm", {}),
    )
