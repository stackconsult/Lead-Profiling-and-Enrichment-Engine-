from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from backend.core.valkey import valkey_client

router = APIRouter(prefix="", tags=["workspaces"])


def _decode(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode()
    return value


def _decode_map(data: Dict[Any, Any]) -> Dict[str, Any]:
    return {str(_decode(k)): _decode(v) for k, v in data.items()}


@router.post("/workspaces")
async def add_workspace(payload: Dict[str, Any]) -> Dict[str, str]:
    provider = payload.get("provider")
    if provider not in {"openai", "gemini"}:
        raise HTTPException(status_code=400, detail="provider must be 'openai' or 'gemini'")
    keys: Dict[str, Optional[str]] = payload.get("keys") or {}

    workspace_id = payload.get("workspace_id") or str(uuid.uuid4())
    mapping = {
        "provider": provider,
        "openai_key": keys.get("openai_key") or "",
        "gemini_key": keys.get("gemini_key") or "",
        "tavily_key": keys.get("tavily_key") or "",
    }
    valkey_client.hset(f"workspaces:{workspace_id}:keys", mapping=mapping)
    return {"workspace_id": workspace_id}


@router.get("/workspaces")
async def list_workspaces() -> Dict[str, List[Dict[str, Any]]]:
    keys = [
        k.decode() if isinstance(k, (bytes, bytearray)) else k
        for k in valkey_client.keys("workspaces:*:keys")
    ]
    items: List[Dict[str, Any]] = []
    for key in keys:
        data = valkey_client.hgetall(key)
        if data:
            parts = str(key).split(":")
            workspace_id = parts[1] if len(parts) > 2 else str(key)
            items.append(_decode_map(data) | {"id": workspace_id})
    return {"items": items}
