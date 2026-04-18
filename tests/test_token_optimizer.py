"""Tests for token optimizer."""

from core.token_optimizer import TokenOptimizer


def test_estimate_prune_and_deduplicate() -> None:
    optimizer = TokenOptimizer({"max_tokens_per_agent": 10, "compression_threshold": 5})
    context = "alpha beta gamma\n\nalpha beta gamma\n\ntask specific delta epsilon"
    deduped = optimizer.deduplicate(context.split("\n\n"))
    assert len(deduped) == 2

    pruned = optimizer.prune_context(context, max_tokens=5, task="task delta")
    assert optimizer.estimate_tokens(pruned) <= 5


def test_budget_enforcement() -> None:
    optimizer = TokenOptimizer({"max_tokens_per_agent": 5, "max_total_tokens": 5})
    optimizer.enforce_budget(5)
    optimizer.record_usage(5)
    try:
        optimizer.enforce_budget(1)
        raised = False
    except ValueError:
        raised = True
    assert raised is True
