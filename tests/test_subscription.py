"""Tests for subscription tier rate limiting and enforcement."""

from __future__ import annotations

import json
import time

import pytest

from token_infra.subscription import (
    SUBSCRIPTION_TIERS,
    SubscriptionError,
    SubscriptionRateLimiter,
    TierLimits,
)


# ---------------------------------------------------------------------------
# TierLimits dataclass
# ---------------------------------------------------------------------------

class TestTierLimits:
    def test_all_tiers_defined(self) -> None:
        assert "free" in SUBSCRIPTION_TIERS
        assert "pro" in SUBSCRIPTION_TIERS
        assert "team" in SUBSCRIPTION_TIERS
        assert "unlimited" in SUBSCRIPTION_TIERS

    def test_pro_has_sensible_defaults(self) -> None:
        pro = SUBSCRIPTION_TIERS["pro"]
        assert pro.requests_per_minute > 0
        assert pro.daily_token_cap > 0
        assert pro.max_tokens_per_request > 0

    def test_unlimited_has_no_daily_cap(self) -> None:
        assert SUBSCRIPTION_TIERS["unlimited"].daily_token_cap == 0


# ---------------------------------------------------------------------------
# SubscriptionRateLimiter — construction
# ---------------------------------------------------------------------------

class TestRateLimiterConstruction:
    def test_create_with_known_tier(self) -> None:
        limiter = SubscriptionRateLimiter(tier="pro")
        assert limiter.tier == "pro"
        assert limiter.limits.requests_per_minute == SUBSCRIPTION_TIERS["pro"].requests_per_minute

    def test_case_insensitive_tier(self) -> None:
        limiter = SubscriptionRateLimiter(tier="Pro")
        assert limiter.tier == "pro"

    def test_unknown_tier_raises(self) -> None:
        with pytest.raises(SubscriptionError, match="Unknown subscription tier"):
            SubscriptionRateLimiter(tier="enterprise_ultra")

    def test_overrides_applied(self) -> None:
        limiter = SubscriptionRateLimiter(tier="pro", overrides={"daily_token_cap": 100_000})
        assert limiter.limits.daily_token_cap == 100_000
        # non-overridden values stay at tier default
        assert limiter.limits.requests_per_minute == SUBSCRIPTION_TIERS["pro"].requests_per_minute


# ---------------------------------------------------------------------------
# Daily token cap enforcement
# ---------------------------------------------------------------------------

class TestDailyTokenCap:
    def test_usage_within_cap_succeeds(self) -> None:
        limiter = SubscriptionRateLimiter(tier="pro", overrides={"daily_token_cap": 1000})
        limiter.check_request(500)  # should not raise

    def test_usage_exceeding_cap_raises(self) -> None:
        limiter = SubscriptionRateLimiter(tier="pro", overrides={"daily_token_cap": 1000})
        limiter.record_usage(800)
        with pytest.raises(SubscriptionError, match="Daily token cap"):
            limiter.check_request(300)

    def test_unlimited_tier_no_cap(self) -> None:
        limiter = SubscriptionRateLimiter(tier="unlimited")
        limiter.record_usage(999_999_999)
        limiter.check_request(999_999)  # should not raise

    def test_record_usage_accumulates(self) -> None:
        limiter = SubscriptionRateLimiter(tier="pro", overrides={"daily_token_cap": 5000})
        limiter.record_usage(1000)
        limiter.record_usage(2000)
        status = limiter.get_status()
        assert status["daily_tokens_used"] == 3000
        assert status["daily_tokens_remaining"] == 2000


# ---------------------------------------------------------------------------
# Rate limit enforcement
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_within_rate_limit(self) -> None:
        limiter = SubscriptionRateLimiter(tier="pro", overrides={"requests_per_minute": 5})
        for _ in range(5):
            limiter.record_request()
        # 5 recorded, next check_request should fail
        with pytest.raises(SubscriptionError, match="Rate limit"):
            limiter.check_request(1)

    def test_wait_if_needed_blocks_on_rate_limit(self) -> None:
        """With a tiny rate window, wait_if_needed should return quickly once capacity opens."""
        limiter = SubscriptionRateLimiter(
            tier="pro",
            overrides={"requests_per_minute": 2, "daily_token_cap": 999_999},
        )
        # Exhaust rate limit
        limiter.record_request()
        limiter.record_request()
        # Manually clear timestamps to simulate time passing
        limiter._request_timestamps = []
        waited = limiter.wait_if_needed(1)
        assert waited == 0.0  # capacity was immediately available after clearing


# ---------------------------------------------------------------------------
# clamp_max_tokens
# ---------------------------------------------------------------------------

class TestClampMaxTokens:
    def test_clamp_reduces_large_value(self) -> None:
        limiter = SubscriptionRateLimiter(tier="free")
        assert limiter.clamp_max_tokens(8000) == SUBSCRIPTION_TIERS["free"].max_tokens_per_request

    def test_clamp_keeps_small_value(self) -> None:
        limiter = SubscriptionRateLimiter(tier="team")
        assert limiter.clamp_max_tokens(100) == 100


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_status_contains_required_keys(self) -> None:
        limiter = SubscriptionRateLimiter(tier="pro")
        status = limiter.get_status()
        assert "tier" in status
        assert "daily_tokens_used" in status
        assert "daily_token_cap" in status
        assert "daily_tokens_remaining" in status
        assert "daily_requests" in status
        assert "requests_per_minute_limit" in status
        assert "max_tokens_per_request" in status

    def test_unlimited_remaining_is_negative_one(self) -> None:
        limiter = SubscriptionRateLimiter(tier="unlimited")
        assert limiter.get_status()["daily_tokens_remaining"] == -1


# ---------------------------------------------------------------------------
# Integration with ClaudeAdapter
# ---------------------------------------------------------------------------

class TestClaudeAdapterIntegration:
    def test_adapter_accepts_subscription_limiter(self) -> None:
        from token_infra.adapters.claude_adapter import ClaudeAdapter

        limiter = SubscriptionRateLimiter(tier="pro")
        adapter = ClaudeAdapter(subscription_limiter=limiter)
        assert adapter.subscription_limiter is limiter

    def test_adapter_estimate_tokens(self) -> None:
        from token_infra.adapters.claude_adapter import ClaudeAdapter

        estimate = ClaudeAdapter._estimate_request_tokens("system prompt text", "user prompt text", 500)
        assert estimate > 500  # includes prompt words + max_response


# ---------------------------------------------------------------------------
# CLI subscription-status command
# ---------------------------------------------------------------------------

class TestCLISubscription:
    def test_cli_subscription_status(self, monkeypatch, tmp_path, capsys) -> None:
        from pathlib import Path
        monkeypatch.chdir(Path(__file__).resolve().parents[1])
        from cli.swarm_cli import main
        ret = main(["subscription-status"])
        assert ret == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "tier" in output

    def test_cli_run_with_tier_override(self, monkeypatch, tmp_path, capsys) -> None:
        from pathlib import Path
        monkeypatch.chdir(Path(__file__).resolve().parents[1])
        from cli.swarm_cli import main
        ret = main(["run", "--dry-run", "--subscription-tier", "free", "build a thing"])
        assert ret == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output.get("subscription", {}).get("tier") == "free"


# ---------------------------------------------------------------------------
# Pipeline integration — subscription limiter wired through config
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    def test_controller_has_limiter_from_config(self, monkeypatch) -> None:
        from pathlib import Path
        monkeypatch.chdir(Path(__file__).resolve().parents[1])
        from pipelines.common import build_controller, load_swarm_config

        cfg = load_swarm_config()
        # The default config has subscription.tier = "pro"
        from tests.conftest import TestModel
        controller = build_controller(TestModel(), cfg)
        limiter = getattr(controller, "subscription_limiter", None)
        assert limiter is not None
        assert limiter.tier == "pro"

    def test_controller_without_subscription_config(self, monkeypatch) -> None:
        from pathlib import Path
        monkeypatch.chdir(Path(__file__).resolve().parents[1])
        from pipelines.common import build_controller

        from tests.conftest import TestModel
        controller = build_controller(TestModel(), {})
        limiter = getattr(controller, "subscription_limiter", None)
        assert limiter is None
