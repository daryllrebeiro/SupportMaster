"""Lightweight tenant-scoped token bucket rate limiter."""

from __future__ import annotations

import time
from threading import Lock


class TokenBucket:
    def __init__(self, capacity: float, fill_rate: float) -> None:
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class TenantRateLimiter:
    def __init__(self, default_capacity: float = 10.0, default_fill_rate: float = 1.0) -> None:
        self.default_capacity = default_capacity
        self.default_fill_rate = default_fill_rate
        self.buckets: dict[str, TokenBucket] = {}
        self.lock = Lock()

    def consume(self, tenant_id: str, tokens: float = 1.0) -> bool:
        with self.lock:
            if tenant_id not in self.buckets:
                self.buckets[tenant_id] = TokenBucket(self.default_capacity, self.default_fill_rate)
            bucket = self.buckets[tenant_id]
        return bucket.consume(tokens)
