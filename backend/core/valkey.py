"""
Valkey connection utilities.

Valkey (Redis-compatible) is used for durable job metadata, lead results,
and workspace configuration. This is distinct from Streamlit's UI state.
"""
from __future__ import annotations

import os
from typing import Dict, Iterable, Optional

import redis
from redis import Redis
from redis.connection import ConnectionPool


def _build_pool() -> ConnectionPool:
    url = os.getenv("VALKEY_URL")
    if url:
        return ConnectionPool.from_url(url, max_connections=20, socket_keepalive=True)

    host = os.getenv("VALKEY_HOST", "localhost")
    port = int(os.getenv("VALKEY_PORT", "6379"))
    return ConnectionPool(
        host=host,
        port=port,
        max_connections=20,
        socket_keepalive=True,
    )


_POOL: ConnectionPool = _build_pool()


class FakeValkey:
    """
    Minimal in-memory stand-in for Redis for tests and local dev without a server.
    Supports a small subset of operations used in this project.
    """

    def __init__(self) -> None:
        self.store: Dict[str, Dict[str, str]] = {}
        self._lists: Dict[str, list] = {}
        self.is_fake = True

    # Hash operations
    def hset(self, name: str, mapping: Optional[Dict[str, object]] = None, **kwargs) -> None:
        data = self.store.setdefault(name, {})
        if mapping:
            for k, v in mapping.items():
                data[k] = v
        for k, v in kwargs.items():
            data[k] = v

    def hgetall(self, name: str) -> Dict[str, object]:
        return self.store.get(name, {}).copy()

    def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        data = self.store.setdefault(name, {})
        data[key] = int(data.get(key, 0)) + amount
        return data[key]

    # Key helpers
    def keys(self, pattern: str = "*") -> Iterable[str]:
        if pattern == "*":
            return list(self.store.keys())
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.store if k.startswith(prefix)]
        return [k for k in self.store if k == pattern]

    # List helpers (minimal)
    def lpush(self, name: str, *values: object) -> None:
        lst = self._lists.setdefault(name, [])
        lst[:0] = list(values)

    def lrange(self, name: str, start: int, end: int) -> list:
        lst = self._lists.get(name, [])
        if end == -1:
            return lst[start:]
        return lst[start : end + 1]

    def flushdb(self) -> None:
        self.store.clear()
        self._lists.clear()

    def ping(self) -> bool:
        return True


def get_client() -> Redis | FakeValkey:
    """Return a Redis/Valkey client backed by the shared connection pool."""
    client = redis.Redis(connection_pool=_POOL)
    try:
        client.ping()
        return client
    except Exception:
        return FakeValkey()


valkey_client: Redis | FakeValkey = get_client()


def set_job_status(job_id: str, status: str, progress: float | None = None, error: Optional[str] = None) -> None:
    """Helper to update common job fields."""
    mapping = {"status": status}
    if progress is not None:
        mapping["progress"] = progress
    if error:
        mapping["error"] = error
    valkey_client.hset(f"jobs:{job_id}", mapping=mapping)
