"""Tests for pipeline construction."""

from pipelines import build_code_pipeline, build_repo_build_pipeline, build_research_pipeline


def test_pipeline_builders_return_controller() -> None:
    repo_controller = build_repo_build_pipeline()
    code_controller = build_code_pipeline()
    research_controller = build_research_pipeline()

    assert "planner" in repo_controller.registry.list_agents()
    assert "coder" in code_controller.registry.list_agents()
    assert "researcher" in research_controller.registry.list_agents()
