"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.base_agent import ModelInterface
from pipelines.common import build_controller, load_swarm_config


class TestModel(ModelInterface):
    """Deterministic model for tests."""

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
        if "atomic execution nodes" in system_prompt:
            return json.dumps([
                {"id": "research", "agent": "researcher", "task": "Research requirements", "dependencies": []},
                {"id": "code", "agent": "coder", "task": "Implement solution", "dependencies": ["research"]},
                {"id": "review", "agent": "reviewer", "task": "Review solution", "dependencies": ["code"]},
                {"id": "test", "agent": "tester", "task": "Test solution", "dependencies": ["review"]},
                {"id": "summary", "agent": "summarizer", "task": "Summarize solution", "dependencies": ["test"]},
            ])
        if "findings" in system_prompt:
            return json.dumps({"findings": ["f1"], "sources": ["s1"], "summary": "ok"})
        if "files" in system_prompt:
            return json.dumps({"files": [{"path": "x.py", "content": "print('x')"}], "explanation": "ok"})
        if "issues" in system_prompt:
            return json.dumps({"issues": [], "approved": True, "suggestions": []})
        if "tests" in system_prompt:
            return json.dumps({"tests": [{"name": "test_a", "code": "def test_a():\n    assert 1"}], "coverage_notes": "ok"})
        return json.dumps({"summary": "ok", "highlights": ["h"]})


@pytest.fixture
def controller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide configured controller with isolated state file."""
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    cfg = load_swarm_config()
    instance = build_controller(TestModel(), cfg)
    instance.memory.file_path = tmp_path / "state.json"
    instance.memory._state = {}
    return instance
