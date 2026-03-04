"""Per-group rate limiting for commands."""

import time
from typing import Dict


class RateLimiter:
    """In-memory cooldown tracker. Resets on restart."""

    def __init__(self, cooldown_seconds: int = 60):
        self.cooldown = cooldown_seconds
        self._last_use: Dict[str, float] = {}

    def check(self, key: str) -> bool:
        """Return True if the action is allowed (not on cooldown)."""
        now = time.monotonic()
        last = self._last_use.get(key, 0.0)
        if now - last < self.cooldown:
            return False
        self._last_use[key] = now
        return True

    def remaining(self, key: str) -> int:
        """Seconds remaining on cooldown, or 0 if not on cooldown."""
        now = time.monotonic()
        last = self._last_use.get(key, 0.0)
        left = self.cooldown - (now - last)
        return max(0, int(left))
