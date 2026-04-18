"""Preconfigured pipelines for common swarm execution patterns."""

from .code_pipeline import build_code_pipeline
from .repo_build_pipeline import build_repo_build_pipeline
from .research_pipeline import build_research_pipeline

__all__ = ["build_repo_build_pipeline", "build_research_pipeline", "build_code_pipeline"]
