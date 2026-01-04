from __future__ import annotations

import os
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


@router.get("/workspaces/test")
async def test_workspace_storage() -> Dict[str, Any]:
    """Test endpoint to verify workspace storage and retrieval"""
    from backend.core.valkey import get_client
    
    # Force a fresh connection
    test_client = get_client()
    is_fake = hasattr(test_client, 'is_fake')
    
    # Create a test workspace
    test_id = "connection-test-workspace"
    test_mapping = {
        "provider": "openai",
        "openai_key": "sk-test",
        "gemini_key": "",
        "tavily_key": "",
    }
    
    # Store it
    test_client.hset(f"workspaces:{test_id}:keys", mapping=test_mapping)
    
    # Immediately retrieve it
    stored_data = test_client.hgetall(f"workspaces:{test_id}:keys")
    
    # Check all workspace keys
    all_workspace_keys = [
        k.decode() if isinstance(k, (bytes, bytearray)) else k
        for k in test_client.keys("workspaces:*:keys")
    ]
    
    # Clean up test data
    test_client.delete(f"workspaces:{test_id}:keys")
    
    return {
        "is_fake_valkey": is_fake,
        "test_storage_worked": bool(stored_data),
        "stored_data_keys": list(stored_data.keys()) if stored_data else [],
        "all_workspace_keys": all_workspace_keys,
        "valkey_url": os.getenv("VALKEY_URL", "Not set"),
        "valkey_host": os.getenv("VALKEY_HOST", "Not set"),
        "valkey_port": os.getenv("VALKEY_PORT", "Not set"),
    }


@router.post("/workspaces")
async def add_workspace(payload: WorkspaceCreate) -> Dict[str, str]:
    workspace_id = payload.workspace_id or str(uuid.uuid4())
    mapping = {
        "provider": payload.keys.provider,  # Store provider from keys object
        "openai_key": payload.keys.openai_key or "",
        "gemini_key": payload.keys.gemini_key or "",
        "tavily_key": payload.keys.tavily_key or "",
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
            # Extract workspace_id from "workspaces:{workspace_id}:keys"
            parts = str(key).split(":")
            workspace_id = parts[1] if len(parts) >= 3 else str(key)
            decoded_data = _decode_map(data)
            # Add the workspace_id to the decoded data
            decoded_data["id"] = workspace_id
            items.append(decoded_data)
    return {"items": items}


@router.get("/workspaces/{workspace_id}")
async def get_workspace_detail(workspace_id: str) -> Dict[str, Any]:
    return get_workspace(workspace_id)
