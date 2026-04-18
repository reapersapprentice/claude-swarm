"""Subscription tier awareness and rate limiting for API calls.

Ensures swarm usage stays within the limits of a user's subscription plan
(e.g. Claude Pro) so they never incur unexpected overage charges.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class TierLimits:
    """Rate and usage limits for a subscription tier."""

    requests_per_minute: int
    daily_token_cap: int
    max_tokens_per_request: int
    max_concurrent_requests: int = 1
    description: str = ""


# Conservative defaults that stay well within published plan limits.
# Users can override via swarm_config.yaml.
SUBSCRIPTION_TIERS: Dict[str, TierLimits] = {
    "free": TierLimits(
        requests_per_minute=5,
        daily_token_cap=25_000,
        max_tokens_per_request=1024,
        max_concurrent_requests=1,
        description="Free tier — minimal usage to stay within free allowances",
    ),
    "pro": TierLimits(
        requests_per_minute=25,
        daily_token_cap=300_000,
        max_tokens_per_request=4096,
        max_concurrent_requests=2,
        description="Claude Pro — stays within standard Pro subscription limits",
    ),
    "team": TierLimits(
        requests_per_minute=50,
        daily_token_cap=1_000_000,
        max_tokens_per_request=8192,
        max_concurrent_requests=4,
        description="Claude Team — higher throughput for team plans",
    ),
    "unlimited": TierLimits(
        requests_per_minute=120,
        daily_token_cap=0,  # 0 = no cap
        max_tokens_per_request=16384,
        max_concurrent_requests=8,
        description="API pay-as-you-go — no daily cap, standard API rate limits",
    ),
}


class SubscriptionError(RuntimeError):
    """Raised when a subscription limit would be exceeded."""


class SubscriptionRateLimiter:
    """Thread-safe rate limiter that enforces subscription tier limits.

    Tracks request timestamps and daily token usage to prevent exceeding
    the user's subscription plan allowances.
    """

    def __init__(self, tier: str = "pro", overrides: Optional[Dict[str, Any]] = None) -> None:
        tier_key = tier.lower()
        if tier_key not in SUBSCRIPTION_TIERS:
            raise SubscriptionError(
                f"Unknown subscription tier '{tier}'. "
                f"Available: {', '.join(sorted(SUBSCRIPTION_TIERS))}"
            )
        base = SUBSCRIPTION_TIERS[tier_key]
        ovr = overrides or {}
        self.tier = tier_key
        self.limits = TierLimits(
            requests_per_minute=int(ovr.get("requests_per_minute", base.requests_per_minute)),
            daily_token_cap=int(ovr.get("daily_token_cap", base.daily_token_cap)),
            max_tokens_per_request=int(ovr.get("max_tokens_per_request", base.max_tokens_per_request)),
            max_concurrent_requests=int(ovr.get("max_concurrent_requests", base.max_concurrent_requests)),
            description=base.description,
        )
        self._lock = threading.Lock()
        self._request_timestamps: list[float] = []
        self._daily_tokens_used: int = 0
        self._daily_requests: int = 0
        self._day_start: float = time.time()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_request(self, estimated_tokens: int) -> None:
        """Validate that one more request is allowed. Raises SubscriptionError if not."""
        with self._lock:
            self._rotate_day()
            self._check_daily_cap(estimated_tokens)
            self._check_rate_limit()

    def wait_if_needed(self, estimated_tokens: int) -> float:
        """Block until the request is allowed. Returns seconds waited.

        Raises SubscriptionError only for hard caps (daily token limit).
        """
        with self._lock:
            self._rotate_day()
            self._check_daily_cap(estimated_tokens)

        waited = 0.0
        while True:
            with self._lock:
                if self._has_rate_capacity():
                    self._record_request()
                    return waited
            sleep_time = 1.0
            time.sleep(sleep_time)
            waited += sleep_time

    def record_usage(self, tokens_used: int) -> None:
        """Record actual token usage after a successful request."""
        with self._lock:
            self._rotate_day()
            self._daily_tokens_used += tokens_used

    def record_request(self) -> None:
        """Record that a request was made (for rate-limit tracking)."""
        with self._lock:
            self._record_request()

    def get_status(self) -> Dict[str, Any]:
        """Return current usage status for monitoring."""
        with self._lock:
            self._rotate_day()
            return {
                "tier": self.tier,
                "daily_tokens_used": self._daily_tokens_used,
                "daily_token_cap": self.limits.daily_token_cap,
                "daily_tokens_remaining": max(0, self.limits.daily_token_cap - self._daily_tokens_used)
                if self.limits.daily_token_cap > 0
                else -1,
                "daily_requests": self._daily_requests,
                "requests_per_minute_limit": self.limits.requests_per_minute,
                "max_tokens_per_request": self.limits.max_tokens_per_request,
            }

    def clamp_max_tokens(self, requested: int) -> int:
        """Clamp max_tokens to the subscription tier limit."""
        return min(requested, self.limits.max_tokens_per_request)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rotate_day(self) -> None:
        """Reset daily counters if a new day has started (24h window)."""
        now = time.time()
        if now - self._day_start >= 86400:
            self._daily_tokens_used = 0
            self._daily_requests = 0
            self._day_start = now

    def _check_daily_cap(self, estimated_tokens: int) -> None:
        if self.limits.daily_token_cap <= 0:
            return  # no cap
        projected = self._daily_tokens_used + estimated_tokens
        if projected > self.limits.daily_token_cap:
            remaining = max(0, self.limits.daily_token_cap - self._daily_tokens_used)
            raise SubscriptionError(
                f"Daily token cap would be exceeded for '{self.tier}' tier. "
                f"Used: {self._daily_tokens_used}, "
                f"Remaining: {remaining}, "
                f"Requested: {estimated_tokens}, "
                f"Cap: {self.limits.daily_token_cap}. "
                f"Wait until the daily window resets or upgrade your subscription tier."
            )

    def _check_rate_limit(self) -> None:
        if not self._has_rate_capacity():
            raise SubscriptionError(
                f"Rate limit reached for '{self.tier}' tier "
                f"({self.limits.requests_per_minute} requests/min). "
                f"Use wait_if_needed() for automatic backoff."
            )

    def _has_rate_capacity(self) -> bool:
        now = time.time()
        cutoff = now - 60.0
        self._request_timestamps = [t for t in self._request_timestamps if t > cutoff]
        return len(self._request_timestamps) < self.limits.requests_per_minute

    def _record_request(self) -> None:
        self._request_timestamps.append(time.time())
        self._daily_requests += 1
