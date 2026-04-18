"""Package setup for claude-swarm."""

from setuptools import find_packages, setup

setup(
    name="claude-swarm",
    version="1.0.0",
    description="Deterministic multi-agent orchestration framework for LLM environments",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["PyYAML>=6.0"],
    python_requires=">=3.9",
)
