"""Example of executing claude-swarm for a large codebase task."""

from pipelines.repo_build_pipeline import build_repo_build_pipeline


if __name__ == "__main__":
    controller = build_repo_build_pipeline()
    result = controller.execute("Build a modular service-oriented application architecture")
    print(result.merged_output)
