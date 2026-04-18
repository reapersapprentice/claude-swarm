"""Pipeline builder for research-oriented tasks."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.base_agent import ModelInterface
from core import SwarmController

from .common import EchoModel, build_controller, load_swarm_config


def build_research_pipeline(model: ModelInterface | None = None, token_config: Optional[Dict[str, Any]] = None) -> SwarmController:
    """Return controller configured for planner→research→summarize flow."""
    cfg = load_swarm_config()
    return build_controller(model or EchoModel(), cfg, token_config=token_config)
