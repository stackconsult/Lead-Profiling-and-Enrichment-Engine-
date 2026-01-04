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
    """Build connection pool with proper environment variable handling"""
    url = os.getenv("VALKEY_URL")
    if url:
        print(f"Connecting to Valkey via URL: {url[:20]}...")  # Debug log
        return ConnectionPool.from_url(url, max_connections=20, socket_keepalive=True, socket_connect_timeout=5, socket_timeout=5)

    host = os.getenv("VALKEY_HOST", "localhost")
    port = int(os.getenv("VALKEY_PORT", "6379"))
    print(f"Connecting to Valkey via host: {host}:{port}")  # Debug log
    return ConnectionPool(
        host=host,
        port=port,
        max_connections=20,
        socket_keepalive=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


# Global connection pool - shared across this process
_POOL: ConnectionPool = _build_pool()

# Global FakeValkey instance for testing - shared across this process
_FAKE_VALKEY: Optional[FakeValkey] = None


def _is_ci_environment() -> bool:
    """Check if running in CI/testing environment"""
    return (
        os.getenv("CI") == "true" or
        os.getenv("GITHUB_ACTIONS") == "true" or
        os.getenv("CIRCLECI") == "true"
    )


def _is_production_environment() -> bool:
    """Check if running in true production (not CI/testing)"""
    return bool(os.getenv("RENDER_SERVICE_ID")) and not _is_ci_environment()


def get_client() -> Redis | FakeValkey:
    """Return a Redis/Valkey client - ALWAYS create fresh connection for reliability"""
    global _FAKE_VALKEY
    
    try:
        # Always create a fresh client to avoid cross-container issues
        client = redis.Redis(connection_pool=_POOL)
        result = client.ping()
        if result:
            print("SUCCESS: Fresh Valkey connection established")
            return client
    except Exception as e:
        print(f"Valkey connection failed: {e}")
        
        if _is_production_environment():
            # In production, fail fast - no fallback
            raise RuntimeError(f"CRITICAL: Cannot start production app without working Valkey/Redis instance! Error: {e}")
        else:
            # Development or CI mode - allow fallback to singleton FakeValkey
            print("Falling back to FakeValkey for local development/testing")
            if _FAKE_VALKEY is None:
                _FAKE_VALKEY = FakeValkey()
            return _FAKE_VALKEY
    
    # Fallback for non-production
    if _is_production_environment():
        raise RuntimeError("CRITICAL: Unable to establish Valkey connection in production!")
    
    # Return singleton FakeValkey for testing
    if _FAKE_VALKEY is None:
        _FAKE_VALKEY = FakeValkey()
    return _FAKE_VALKEY


# DO NOT initialize global client at import time - this causes startup failures
# valkey_client: Redis | FakeValkey = get_client()  # REMOVED - causes import-time connection


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
    def hset(self, name: str, key: str = None, value: object = None, mapping: Optional[Dict[str, object]] = None, **kwargs) -> int:
        """Set hash field value - supports both field/value and mapping syntax
        Returns number of fields that were added (not updated)
        """
        data = self.store.setdefault(name, {})
        fields_added = 0
        
        # Support hset(name, field, value) syntax
        if key is not None and value is not None:
            if key not in data:
                fields_added += 1
            data[key] = value
        
        # Support hset(name, mapping={...}) syntax
        if mapping:
            for k, v in mapping.items():
                if k not in data:
                    fields_added += 1
                data[k] = v
        
        # Support hset(name, field1=value1, field2=value2) syntax
        for k, v in kwargs.items():
            if k not in data:
                fields_added += 1
            data[k] = v
        
        return fields_added

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
    def set(self, name: str, value: str, nx: bool = False, ex: int = None) -> bool:
        """Set key with optional NX (not exists) and EX (expiry) flags"""
        if nx and name in self.store:
            return False  # Key exists, cannot set with NX
        
        self.store[name] = {"value": value}
        # Note: FakeValkey doesn't actually implement expiration for simplicity
        return True

    def get(self, name: str) -> Optional[str]:
        data = self.store.get(name, {})
        return data.get("value")

    def delete(self, name: str) -> int:
        """Delete key and return number of keys deleted"""
        count = 0
        if name in self.store:
            self.store.pop(name)
            count += 1
        if name in self._lists:
            self._lists.pop(name)
            count += 1
        return count

    def expire(self, name: str, seconds: int) -> bool:
        """Set expiration on a key - FakeValkey doesn't implement actual expiration"""
        # For testing, we just return True if the key exists
        return name in self.store or name in self._lists

    def ttl(self, name: str) -> int:
        """Get time to live for key - FakeValkey returns -1 (no expiration)"""
        if name in self.store or name in self._lists:
            return -1  # No expiration set
        return -2  # Key doesn't exist

    def eval(self, script: str, num_keys: int, *keys_and_args) -> int:
        """Execute Lua script - SIMPLIFIED implementation for FakeValkey
        
        NOTE: This is a minimal implementation specifically for lock release operations
        used in distributed_workspaces.py. It does not support arbitrary Lua scripts.
        For full Lua script support, use a real Redis/Valkey instance.
        """
        # For FakeValkey, we simplify the Lua script execution
        # This is only used for lock release in distributed_workspaces.py
        if num_keys > 0 and len(keys_and_args) >= num_keys + 1:
            lock_key = keys_and_args[0]
            lock_value = keys_and_args[num_keys]
            
            # Check if lock exists and matches the value
            current_value = self.get(lock_key)
            if current_value == lock_value:
                self.delete(lock_key)
                return 1
        return 0

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


# DO NOT initialize global client at import time - this causes startup failures
# valkey_client: Redis | FakeValkey = get_client()  # REMOVED - causes import-time connection


def set_job_status(job_id: str, status: str, progress: float | None = None, error: Optional[str] = None) -> None:
    """Helper to update common fields."""
    client = get_client()  # Use fresh client instead of global
    mapping = {"status": status}
    if progress is not None:
        mapping["progress"] = progress
    if error:
        mapping["error"] = error
    client.hset(f"jobs:{job_id}", mapping=mapping)
    try:
        payload = json.dumps(mapping)
        client.publish(f"jobs:{job_id}:events", payload)
    except Exception:
        pass  # Best-effort publish
