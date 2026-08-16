"""Per destination rate limiting for the outbound call trigger. A demo
console that becomes a robodialer by holding down a button is a bad
look, so each destination gets a small sliding window rather than an
unlimited button.
"""

import time
from collections import defaultdict

MAX_CALLS_PER_WINDOW = 3
WINDOW_SECONDS = 60


class DestinationRateLimiter:
    def __init__(
        self, max_calls: int = MAX_CALLS_PER_WINDOW, window_seconds: int = WINDOW_SECONDS
    ) -> None:
        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._calls_at: dict[str, list[float]] = defaultdict(list)

    def allow(self, destination: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window_seconds
        recent = [t for t in self._calls_at[destination] if t > cutoff]
        recent.append(now)
        self._calls_at[destination] = recent
        return len(recent) <= self._max_calls
