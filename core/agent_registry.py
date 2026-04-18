"""Agent registry with lazy initialization and capability lookup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AgentSpec:
    """Configuration and factory metadata for a registered agent."""

    name: str
    factory: Callable[..., Any]
    config: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    instance: Optional[Any] = None


class AgentRegistry:
    """Register and retrieve agents by name."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentSpec] = {}

    def register(self, name: str, agent_class: Callable[..., Any], config: Optional[Dict[str, Any]] = None,
                 capabilities: Optional[List[str]] = None) -> None:
        """Register an agent factory and metadata."""
        if name in self._agents:
            raise ValueError(f"Agent '{name}' is already registered")
        self._agents[name] = AgentSpec(
            name=name,
            factory=agent_class,
            config=config or {},
            capabilities=capabilities or [],
        )

    def get(self, name: str) -> Any:
        """Get an agent instance, lazily constructing it on first use."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' is not registered")
        spec = self._agents[name]
        if spec.instance is None:
            spec.instance = spec.factory(**spec.config)
        return spec.instance

    def list_agents(self) -> List[str]:
        """Return sorted registered agent names."""
        return sorted(self._agents.keys())

    def capabilities(self, name: str) -> List[str]:
        """Return capability list for a registered agent."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' is not registered")
        return list(self._agents[name].capabilities)

    def auto_register_defaults(self, defaults: Dict[str, Dict[str, Any]]) -> None:
        """Bulk-register default agent set from a mapping."""
        for name, spec in defaults.items():
            self.register(
                name=name,
                agent_class=spec["factory"],
                config=spec.get("config", {}),
                capabilities=spec.get("capabilities", []),
            )
