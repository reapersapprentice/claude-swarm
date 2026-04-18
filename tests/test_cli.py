"""Tests for CLI parsing and commands."""

from cli.swarm_cli import build_parser, main


def test_parser_run_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "do work", "--pipeline", "code", "--dry-run"])
    assert args.command == "run"
    assert args.pipeline == "code"
    assert args.dry_run is True


def test_main_list_agents(capsys) -> None:
    code = main(["list-agents"])
    output = capsys.readouterr().out
    assert code == 0
    assert "planner" in output
