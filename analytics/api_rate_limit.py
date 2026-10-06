from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

API_RATE_LIMIT_VERSION = "71.0.0"
RATE_LIMIT_BOUNDARY = "API_RATE_LIMIT_BOUNDARY"
RATE_LIMIT_ALLOWED = "RATE_LIMIT_ALLOWED"
RATE_LIMITED = "RATE_LIMITED"
RATE_LIMIT_DENIED = "RATE_LIMIT_DENIED"

@dataclass(frozen=True)
class ApiRateLimitPolicy:
    enabled: bool = True
    requests_per_window: int = 60
    window_seconds: float = 60.0
    burst_limit: int = 10
    burst_window_seconds: float = 1.0

@dataclass(frozen=True)
class RateLimitDecision:
    status: str
    identity: str
    limit: int
    remaining: int
    retry_after: int
    window_seconds: float

    @property
    def allowed(self) -> bool:
        return self.status == RATE_LIMIT_ALLOWED

class ApiRateLimiter:
    def __init__(
        self,
        policy: ApiRateLimitPolicy = ApiRateLimitPolicy(),
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        validate_rate_limit_policy(policy)
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._policy = policy
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._burst_events: dict[str, deque[float]] = {}

    @property
    def policy(self) -> ApiRateLimitPolicy:
        return self._policy

    def reset(self) -> None:
        self._events.clear()
        self._burst_events.clear()

    def _prune(self, identity: str, now: float) -> tuple[deque[float], deque[float]]:
        events = self._events.setdefault(identity, deque())
        burst_events = self._burst_events.setdefault(identity, deque())
        cutoff = now - self._policy.window_seconds
        burst_cutoff = now - self._policy.burst_window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        while burst_events and burst_events[0] <= burst_cutoff:
            burst_events.popleft()
        return events, burst_events

    def check(self, identity: str) -> RateLimitDecision:
        if not isinstance(identity, str) or not identity:
            raise ValueError("identity must be a non-empty string")
        if not self._policy.enabled:
            return RateLimitDecision(
                RATE_LIMIT_ALLOWED, identity, self._policy.requests_per_window,
                self._policy.requests_per_window, 0, self._policy.window_seconds,
            )
        now = float(self._clock())
        events, burst_events = self._prune(identity, now)
        if len(events) >= self._policy.requests_per_window:
            retry = self._policy.window_seconds - (now - events[0])
            return RateLimitDecision(
                RATE_LIMITED, identity, self._policy.requests_per_window, 0,
                max(1, int(retry + 0.999999)), self._policy.window_seconds,
            )
        if len(burst_events) >= self._policy.burst_limit:
            retry = self._policy.burst_window_seconds - (now - burst_events[0])
            remaining = max(0, self._policy.requests_per_window - len(events))
            return RateLimitDecision(
                RATE_LIMITED, identity, self._policy.requests_per_window, remaining,
                max(1, int(retry + 0.999999)), self._policy.window_seconds,
            )
        events.append(now)
        burst_events.append(now)
        remaining = max(0, self._policy.requests_per_window - len(events))
        return RateLimitDecision(
            RATE_LIMIT_ALLOWED, identity, self._policy.requests_per_window, remaining, 0,
            self._policy.window_seconds,
        )

def validate_rate_limit_policy(policy: ApiRateLimitPolicy) -> None:
    if not isinstance(policy, ApiRateLimitPolicy):
        raise TypeError("policy must be ApiRateLimitPolicy")
    if not isinstance(policy.enabled, bool):
        raise ValueError("enabled must be boolean")
    if (
        isinstance(policy.requests_per_window, bool)
        or not isinstance(policy.requests_per_window, int)
        or policy.requests_per_window <= 0
    ):
        raise ValueError("requests_per_window must be a positive integer")
    if (
        isinstance(policy.window_seconds, bool)
        or not isinstance(policy.window_seconds, (int, float))
        or policy.window_seconds <= 0
    ):
        raise ValueError("window_seconds must be a positive number")
    if (
        isinstance(policy.burst_limit, bool)
        or not isinstance(policy.burst_limit, int)
        or policy.burst_limit <= 0
    ):
        raise ValueError("burst_limit must be a positive integer")
    if policy.burst_limit > policy.requests_per_window:
        raise ValueError("burst_limit cannot exceed requests_per_window")
    if (
        isinstance(policy.burst_window_seconds, bool)
        or not isinstance(policy.burst_window_seconds, (int, float))
        or policy.burst_window_seconds <= 0
        or policy.burst_window_seconds > policy.window_seconds
    ):
        raise ValueError("burst_window_seconds must be positive and not exceed window_seconds")

def rate_limit_summary(policy: ApiRateLimitPolicy, limiter: ApiRateLimiter) -> dict[str, object]:
    validate_rate_limit_policy(policy)
    if limiter.policy != policy:
        raise ValueError("limiter policy does not match supplied policy")
    return {
        "version": API_RATE_LIMIT_VERSION,
        "boundary": RATE_LIMIT_BOUNDARY,
        "enabled": policy.enabled,
        "requests_per_window": policy.requests_per_window,
        "window_seconds": policy.window_seconds,
        "burst_limit": policy.burst_limit,
        "burst_window_seconds": policy.burst_window_seconds,
        "tracked_identities": len(limiter._events),
    }

def rate_limit_headers(decision: RateLimitDecision) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
        "X-RateLimit-Window": str(decision.window_seconds),
        "Retry-After": str(decision.retry_after),
    }

__all__ = [
    "API_RATE_LIMIT_VERSION",
    "RATE_LIMIT_BOUNDARY",
    "RATE_LIMIT_ALLOWED",
    "RATE_LIMITED",
    "RATE_LIMIT_DENIED",
    "ApiRateLimitPolicy",
    "RateLimitDecision",
    "ApiRateLimiter",
    "validate_rate_limit_policy",
    "rate_limit_summary",
    "rate_limit_headers",
]
