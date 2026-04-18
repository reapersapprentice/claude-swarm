"""Tests that all agents properly handle invalid JSON with narrowed exception handling.

Each agent's _parse (or _parse_or_fallback) method catches
(json.JSONDecodeError, ValueError, KeyError, TypeError) and returns a
deterministic fallback instead of propagating.
"""

import json
from pathlib import Path

import pytest

from agents.base_agent import ModelInterface
from agents.coder_agent import CoderAgent
from agents.researcher_agent import ResearcherAgent
from agents.reviewer_agent import ReviewerAgent
from agents.tester_agent import TesterAgent
from agents.summarizer_agent import SummarizerAgent
from agents.planner_agent import PlannerAgent


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

class StubModel(ModelInterface):
    def __init__(self, response="{}"):
        self.response = response

    def generate(self, system_prompt, user_prompt, max_tokens, temperature=0.0):
        return self.response


@pytest.fixture
def prompt_file(tmp_path):
    p = tmp_path / "test_prompt.txt"
    p.write_text("You are a test agent.")
    return str(p)


# ---------------------------------------------------------------------------
# CoderAgent
# ---------------------------------------------------------------------------

class TestCoderAgentParse:
    def test_invalid_json_returns_fallback(self, prompt_file):
        agent = CoderAgent(name="coder", prompt_path=prompt_file, model=StubModel())
        result = agent._parse("NOT JSON {{{", "build widget")
        assert "files" in result
        assert "explanation" in result
        assert isinstance(result["files"], list)

    def test_valid_json_returns_parsed(self, prompt_file):
        valid = json.dumps({"files": [{"path": "a.py", "content": "x=1"}], "explanation": "done"})
        agent = CoderAgent(name="coder", prompt_path=prompt_file, model=StubModel())
        result = agent._parse(valid, "build widget")
        assert result["files"][0]["path"] == "a.py"
        assert result["explanation"] == "done"


# ---------------------------------------------------------------------------
# ResearcherAgent
# ---------------------------------------------------------------------------

class TestResearcherAgentParse:
    def test_garbage_returns_fallback(self, prompt_file):
        agent = ResearcherAgent(name="researcher", prompt_path=prompt_file, model=StubModel())
        result = agent._parse("~~~garbage~~~", "investigate topic")
        assert "findings" in result
        assert "sources" in result
        assert "summary" in result
        assert isinstance(result["findings"], list)
        assert isinstance(result["sources"], list)


# ---------------------------------------------------------------------------
# ReviewerAgent
# ---------------------------------------------------------------------------

class TestReviewerAgentParse:
    def test_malformed_json_returns_fallback(self, prompt_file):
        agent = ReviewerAgent(name="reviewer", prompt_path=prompt_file, model=StubModel())
        result = agent._parse("{malformed")
        assert result["approved"] is True
        assert "issues" in result
        assert "suggestions" in result


# ---------------------------------------------------------------------------
# TesterAgent
# ---------------------------------------------------------------------------

class TestTesterAgentParse:
    def test_bad_json_returns_fallback(self, prompt_file):
        agent = TesterAgent(name="tester", prompt_path=prompt_file, model=StubModel())
        result = agent._parse("no json here", "test login")
        assert "tests" in result
        assert isinstance(result["tests"], list)
        assert "coverage_notes" in result


# ---------------------------------------------------------------------------
# SummarizerAgent
# ---------------------------------------------------------------------------

class TestSummarizerAgentParse:
    def test_non_json_returns_fallback(self, prompt_file):
        agent = SummarizerAgent(name="summarizer", prompt_path=prompt_file, model=StubModel())
        result = agent._parse("plain text summary", "some context words")
        assert "summary" in result
        assert isinstance(result["summary"], str)


# ---------------------------------------------------------------------------
# PlannerAgent
# ---------------------------------------------------------------------------

class TestPlannerAgentParseFallback:
    def test_invalid_json_returns_default_plan(self, prompt_file):
        agent = PlannerAgent(name="planner", prompt_path=prompt_file, model=StubModel())
        result = agent._parse_or_fallback("<<<invalid>>>", "deploy service")
        assert isinstance(result, list)
        assert len(result) == 5
        ids = {node["id"] for node in result}
        assert ids == {"research", "code", "review", "test", "summary"}
        for node in result:
            assert "agent" in node
            assert "task" in node
