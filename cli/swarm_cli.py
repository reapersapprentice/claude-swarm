"""CLI for running and inspecting claude-swarm pipelines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from memory.context_cache import ContextCache
from pipelines import build_code_pipeline, build_repo_build_pipeline, build_research_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Create command-line parser."""
    parser = argparse.ArgumentParser(prog="claude-swarm")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("task", type=str)
    run_parser.add_argument("--pipeline", choices=["repo", "research", "code"], default="repo")
    run_parser.add_argument("--dry-run", action="store_true")

    show_graph_parser = subparsers.add_parser("show-graph")
    show_graph_parser.add_argument("task", type=str)
    show_graph_parser.add_argument("--pipeline", choices=["repo", "research", "code"], default="repo")

    subparsers.add_parser("list-agents")
    subparsers.add_parser("clear-cache")
    return parser


def get_controller(pipeline: str):
    """Construct controller based on selected pipeline."""
    if pipeline == "research":
        return build_research_pipeline()
    if pipeline == "code":
        return build_code_pipeline()
    return build_repo_build_pipeline()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "clear-cache":
        ContextCache().clear()
        print("Cache cleared")
        return 0

    controller = get_controller(getattr(args, "pipeline", "repo"))

    if args.command == "list-agents":
        print("\n".join(controller.registry.list_agents()))
        return 0

    if args.command == "run":
        result = controller.execute(args.task, dry_run=args.dry_run)
        payload: dict[str, Any] = {
            "success": result.success,
            "merged_output": result.merged_output,
            "metrics": result.metrics,
        }
        if args.dry_run:
            payload["graph"] = result.graph_visualization
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "show-graph":
        result = controller.execute(args.task, dry_run=True)
        print(result.graph_visualization)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
