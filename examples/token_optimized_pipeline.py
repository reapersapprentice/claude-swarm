"""Example: run repo_build pipeline with and without token infrastructure."""

from __future__ import annotations

import json

from pipelines.repo_build_pipeline import build_repo_build_pipeline


def main() -> None:
    task = "Implement repository bootstrap workflow with tests"

    baseline = build_repo_build_pipeline()
    baseline_result = baseline.execute(task)

    optimized = build_repo_build_pipeline(
        token_config={
            "prompt_schema_path": "configs/prompt_schema.yaml",
            "budgets_path": "configs/budgets.yaml",
            "prefer_chromadb": False,
            "retrieval_top_k": 3,
        }
    )
    optimized_result = optimized.execute(task)

    comparison = {
        "baseline_tokens": baseline_result.metrics.get("tokens_used", 0),
        "optimized_tokens": optimized_result.metrics.get("tokens_used", 0),
        "baseline_success": baseline_result.success,
        "optimized_success": optimized_result.success,
    }
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
