from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.valkey import valkey_client

router = APIRouter(prefix="", tags=["workspaces"])


def _decode(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode()
    return value


def _decode_map(data: Dict[Any, Any]) -> Dict[str, Any]:
    return {str(_decode(k)): _decode(v) for k, v in data.items()}


class WorkspaceKeys(BaseModel):
    provider: str = Field(..., pattern="^(openai|gemini)$")
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None
    tavily_key: Optional[str] = None


class WorkspaceCreate(BaseModel):
    provider: str = Field(..., pattern="^(openai|gemini)$")
    workspace_id: Optional[str] = None
    keys: WorkspaceKeys


def get_workspace(workspace_id: str) -> Dict[str, str]:
    data = valkey_client.hgetall(f"workspaces:{workspace_id}:keys")
    if not data:
        raise HTTPException(status_code=404, detail="workspace not found")
    decoded = _decode_map(data)
    decoded["id"] = workspace_id
    return decoded


@router.post("/workspaces")
async def add_workspace(payload: WorkspaceCreate) -> Dict[str, str]:
    workspace_id = payload.workspace_id or str(uuid.uuid4())
    mapping = {
        "provider": payload.keys.provider,  # Store provider from keys object
        "openai_key": payload.keys.openai_key or "",
        "gemini_key": payload.keys.gemini_key or "",
        "tavily_key": payload.keys.tavily_key or "",
    }
    
    # Debug: Log what we're storing
    print(f"DEBUG: Storing workspace {workspace_id} with mapping: {mapping}")
    print(f"DEBUG: Valkey client type: {type(valkey_client)}")
    print(f"DEBUG: Is fake valkey: {hasattr(valkey_client, 'is_fake')}")
    
    valkey_client.hset(f"workspaces:{workspace_id}:keys", mapping=mapping)
    
    # Debug: Verify it was stored
    stored_data = valkey_client.hgetall(f"workspaces:{workspace_id}:keys")
    print(f"DEBUG: Retrieved stored data: {stored_data}")
    
    return {"workspace_id": workspace_id}


@router.get("/workspaces")
async def list_workspaces() -> Dict[str, List[Dict[str, Any]]]:
    # Check if we're using fake or real valkey
    is_fake = hasattr(valkey_client, 'is_fake')
    
    # Debug: Log all keys found
    all_keys = [
        k.decode() if isinstance(k, (bytes, bytearray)) else k
        for k in valkey_client.keys("*")
    ]
    workspace_keys = [
        k.decode() if isinstance(k, (bytes, bytearray)) else k
        for k in valkey_client.keys("workspaces:*:keys")
    ]
    
    # Return debug info temporarily
    debug_info = {
        "is_fake_valkey": is_fake,
        "all_keys": all_keys,
        "workspace_keys": workspace_keys,
        "items": []
    }
    
    keys = workspace_keys
    items: List[Dict[str, Any]] = []
    for key in keys:
        data = valkey_client.hgetall(key)
        debug_info["debug_data_for_key"] = {key: str(data)}
        if data:
            # Extract workspace_id from "workspaces:{workspace_id}:keys"
            parts = str(key).split(":")
            workspace_id = parts[1] if len(parts) >= 3 else str(key)
            decoded_data = _decode_map(data)
            # Add the workspace_id to the decoded data
            decoded_data["id"] = workspace_id
            items.append(decoded_data)
    
    debug_info["items"] = items
    return debug_info


@router.get("/workspaces/{workspace_id}")
async def get_workspace_detail(workspace_id: str) -> Dict[str, Any]:
    return get_workspace(workspace_id)
