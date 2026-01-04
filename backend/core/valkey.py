"""
Valkey connection utilities.

Valkey (Redis-compatible) is used for durable job metadata, lead results,
and workspace configuration. This is distinct from Streamlit's UI state.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Iterable, Optional

import redis
from redis import Redis
from redis.connection import ConnectionPool


def _build_pool() -> ConnectionPool:
    url = os.getenv("VALKEY_URL")
    if url:
        print(f"Connecting to Valkey via URL: {url[:20]}...")  # Debug log
        return ConnectionPool.from_url(url, max_connections=20, socket_keepalive=True)

    host = os.getenv("VALKEY_HOST", "localhost")
    port = int(os.getenv("VALKEY_PORT", "6379"))
    print(f"Connecting to Valkey via host: {host}:{port}")  # Debug log
    return ConnectionPool(
        host=host,
        port=port,
        max_connections=20,
        socket_keepalive=True,
    )


# Global client instance to ensure consistency across requests
_valkey_client: Redis | FakeValkey | None = None
_POOL: ConnectionPool | None = None

def _get_pool() -> ConnectionPool:
    """Get or create connection pool with proper environment variable handling"""
    global _POOL
    if _POOL is None:
        _POOL = _build_pool()
    return _POOL

def get_client() -> Redis | FakeValkey:
    """Return a Redis/Valkey client backed by the shared connection pool."""
    global _valkey_client
    
    if _valkey_client is not None:
        # Return existing client if it's still connected
        try:
            if hasattr(_valkey_client, 'ping'):
                _valkey_client.ping()
                return _valkey_client
        except Exception:
            # Connection failed, reset and try again
            _valkey_client = None
    
    # Create new client with fresh pool
    pool = _get_pool()
    client = redis.Redis(connection_pool=pool)
    try:
        result = client.ping()
        if result:
            _valkey_client = client
            print("SUCCESS: Valkey connection established")
            return client
    except Exception as e:
        print(f"Valkey connection failed: {e}")
        # In production, we should fail rather than use FakeValkey
        # But for local development, we can fall back
        if os.getenv("RENDER_SERVICE_ID"):  # We're on Render
            raise Exception(f"Valkey connection required in production: {e}")
        else:
            print("Falling back to FakeValkey for local development")
            _valkey_client = FakeValkey()
            return _valkey_client
    
    _valkey_client = FakeValkey()
    return _valkey_client


class FakeValkey:
    """
    Minimal in-memory stand-in for Redis for tests and local dev without a server.
    Supports a small subset of operations used in this project.
    """

    def __init__(self) -> None:
        self.store: Dict[str, Dict[str, str]] = {}
        self._lists: Dict[str, list] = {}
        self._channels: Dict[str, list] = {}
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

    # Additional operations needed
    def set(self, name: str, value: str) -> None:
        self.store[name] = {"value": value}

    def get(self, name: str) -> Optional[str]:
        data = self.store.get(name, {})
        return data.get("value")

    def delete(self, name: str) -> None:
        self.store.pop(name, None)
        self._lists.pop(name, None)

    # Pub/Sub minimal stubs
    def publish(self, channel: str, message: str) -> None:
        self._channels.setdefault(channel, []).append(message)

    class _FakePubSub:
        def __init__(self, channels: Dict[str, list]):
            self.channels = channels
            self._subs: list[str] = []

        def subscribe(self, channel: str):
            if channel not in self._subs:
                self._subs.append(channel)

        def get_message(self, timeout: float | None = None):
            for ch in list(self._subs):
                items = self.channels.get(ch, [])
                if items:
                    data = items.pop(0)
                    return {"type": "message", "data": data}
            return None

        def close(self):
            self._subs.clear()

    def pubsub(self):
        return self._FakePubSub(self._channels)

    def flushdb(self) -> None:
        self.store.clear()
        self._lists.clear()

    def ping(self) -> bool:
        return True


valkey_client: Redis | FakeValkey = get_client()


def set_job_status(job_id: str, status: str, progress: float | None = None, error: Optional[str] = None) -> None:
    """Helper to update common job fields."""
    mapping = {"status": status}
    if progress is not None:
        mapping["progress"] = progress
    if error:
        mapping["error"] = error
    valkey_client.hset(f"jobs:{job_id}", mapping=mapping)
    try:
        payload = json.dumps(mapping)
        valkey_client.publish(f"jobs:{job_id}:events", payload)
    except Exception:
        # Best-effort publish
        pass
