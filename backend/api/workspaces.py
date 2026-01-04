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


@router.post("/workspaces")
async def add_workspace(payload: WorkspaceCreate) -> Dict[str, str]:
    workspace_id = payload.workspace_id or str(uuid.uuid4())
    mapping = {
        "provider": payload.keys.provider,  # Store provider from keys object
        "openai_key": payload.keys.openai_key or "",
        "gemini_key": payload.keys.gemini_key or "",
        "tavily_key": payload.keys.tavily_key or "",
    }
    
    # Force fresh connection for each write operation
    from backend.core.valkey import get_client
    fresh_client = get_client()
    
    try:
        fresh_client.hset(f"workspaces:{workspace_id}:keys", mapping=mapping)
        
        # Verify it was stored
        stored_data = fresh_client.hgetall(f"workspaces:{workspace_id}:keys")
        if not stored_data:
            raise Exception("Failed to store workspace data")
            
        print(f"SUCCESS: Stored workspace {workspace_id}")
        return {"workspace_id": workspace_id}
        
    except Exception as e:
        print(f"ERROR storing workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store workspace: {e}")


@router.get("/workspaces")
async def list_workspaces() -> Dict[str, List[Dict[str, Any]]]:
    # Force fresh connection for each read operation
    from backend.core.valkey import get_client
    fresh_client = get_client()
    
    try:
        # Get all workspace keys
        workspace_keys = fresh_client.keys("workspaces:*:keys")
        
        print(f"DEBUG: Found {len(workspace_keys)} workspace keys")
        
        items: List[Dict[str, Any]] = []
        for key in workspace_keys:
            key_str = key.decode() if isinstance(key, (bytes, bytearray)) else key
            data = fresh_client.hgetall(key)
            
            if data:
                # Extract workspace_id from "workspaces:{workspace_id}:keys"
                parts = key_str.split(":")
                workspace_id = parts[1] if len(parts) >= 3 else key_str
                
                decoded_data = _decode_map(data)
                decoded_data["id"] = workspace_id
                items.append(decoded_data)
                
                print(f"SUCCESS: Found workspace {workspace_id}")
        
        print(f"DEBUG: Returning {len(items)} workspaces")
        return {"items": items}
        
    except Exception as e:
        print(f"ERROR in list_workspaces: {e}")
        raise HTTPException(status_code=500, detail=f"Workspace retrieval failed: {e}")


@router.get("/workspaces/{workspace_id}")
async def get_workspace_detail(workspace_id: str) -> Dict[str, Any]:
    return get_workspace(workspace_id)
