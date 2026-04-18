"""Example of executing claude-swarm for a research task."""

from pipelines.research_pipeline import build_research_pipeline


if __name__ == "__main__":
    controller = build_research_pipeline()
    result = controller.execute("Research state-of-the-art approaches for retrieval-augmented generation")
    print(result.merged_output)
