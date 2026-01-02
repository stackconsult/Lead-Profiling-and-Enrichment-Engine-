"""
Simple in-memory token bucket rate limiter.

This is intended for per-process throttling to avoid hammering LLM providers.
For distributed limits, implement with Valkey-backed counters instead.
"""
from __future__ import annotations

import asyncio
import time
from typing import Dict


class TokenBucket:
    def __init__(self, rate: int, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, amount: int = 1) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated_at
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.updated_at = now
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False


class RateLimiter:
    """
    Maintains token buckets by key (e.g., workspace_id).
    """

    def __init__(self, rate: int, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self._buckets: Dict[str, TokenBucket] = {}

    def _get_bucket(self, key: str) -> TokenBucket:
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(self.rate, self.capacity)
        return self._buckets[key]

    async def allow(self, key: str, amount: int = 1) -> bool:
        bucket = self._get_bucket(key)
        return await bucket.consume(amount)
