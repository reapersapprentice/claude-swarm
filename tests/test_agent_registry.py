"""Tests for agent registry."""

from core.agent_registry import AgentRegistry


class DummyAgent:
    """Simple test agent."""

    def __init__(self, value: str = "ok") -> None:
        self.value = value


def test_register_and_lazy_get() -> None:
    registry = AgentRegistry()
    registry.register("dummy", DummyAgent, config={"value": "x"}, capabilities=["test"])

    agent = registry.get("dummy")
    assert agent.value == "x"
    assert registry.capabilities("dummy") == ["test"]


def test_duplicate_registration_blocked() -> None:
    registry = AgentRegistry()
    registry.register("dummy", DummyAgent)
    try:
        registry.register("dummy", DummyAgent)
        raised = False
    except ValueError:
        raised = True
    assert raised is True
