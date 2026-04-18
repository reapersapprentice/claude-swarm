"""CLI for running and inspecting claude-swarm pipelines."""

from __future__ import annotations

import argparse
import json
from typing import Any

from memory.context_cache import ContextCache
from pipelines import build_code_pipeline, build_repo_build_pipeline, build_research_pipeline
from token_infra.subscription import SUBSCRIPTION_TIERS


def build_parser() -> argparse.ArgumentParser:
    """Create command-line parser."""
    parser = argparse.ArgumentParser(prog="claude-swarm")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("task", type=str)
    run_parser.add_argument("--pipeline", choices=["repo", "research", "code"], default="repo")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument(
        "--subscription-tier",
        choices=sorted(SUBSCRIPTION_TIERS),
        default=None,
        help="Override the subscription tier from config (e.g. free, pro, team, unlimited)",
    )

    show_graph_parser = subparsers.add_parser("show-graph")
    show_graph_parser.add_argument("task", type=str)
    show_graph_parser.add_argument("--pipeline", choices=["repo", "research", "code"], default="repo")

    subparsers.add_parser("list-agents")
    subparsers.add_parser("clear-cache")
    subparsers.add_parser("subscription-status", help="Show current subscription tier and usage")
    return parser


def get_controller(pipeline: str, subscription_tier: str | None = None) -> Any:
    """Construct controller based on selected pipeline and optional tier override."""
    # Build the controller; the config file provides the default tier.
    if pipeline == "research":
        ctrl = build_research_pipeline()
    elif pipeline == "code":
        ctrl = build_code_pipeline()
    else:
        ctrl = build_repo_build_pipeline()

    # If the user passed --subscription-tier, override what the config had.
    if subscription_tier is not None:
        from token_infra.subscription import SubscriptionRateLimiter
        ctrl.subscription_limiter = SubscriptionRateLimiter(tier=subscription_tier)

    return ctrl


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "clear-cache":
        ContextCache().clear()
        print("Cache cleared")
        return 0

    if args.command == "subscription-status":
        ctrl = get_controller("repo")
        limiter = getattr(ctrl, "subscription_limiter", None)
        if limiter is None:
            print("No subscription tier configured.")
        else:
            print(json.dumps(limiter.get_status(), indent=2))
        return 0

    controller = get_controller(
        getattr(args, "pipeline", "repo"),
        getattr(args, "subscription_tier", None),
    )

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
        # Include subscription usage if a limiter is active
        limiter = getattr(controller, "subscription_limiter", None)
        if limiter is not None:
            payload["subscription"] = limiter.get_status()
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
