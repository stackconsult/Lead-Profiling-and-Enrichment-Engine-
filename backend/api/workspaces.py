from __future__ import annotations

import os
import time
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field

from backend.core.valkey import get_client


router = APIRouter(prefix="", tags=["workspaces"])


class WorkspaceKeys(BaseModel):
    provider: str
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None
    tavily_key: Optional[str] = None


class WorkspaceCreate(BaseModel):
    workspace_id: Optional[str] = None
    provider: str
    keys: WorkspaceKeys


def _decode_map(data: Dict[bytes, bytes]) -> Dict[str, str]:
    return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}


def verify_token(x_api_token: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("API_TOKEN")
    if expected and x_api_token != expected:
        raise HTTPException(status_code=401, detail="invalid API token")


def get_workspace(workspace_id: str) -> Dict[str, str]:
    # ALWAYS get fresh client for cross-container reliability
    client = get_client()
    data = client.hgetall(f"workspaces:{workspace_id}:keys")
    if not data:
        raise HTTPException(status_code=404, detail="workspace not found")
    decoded = _decode_map(data)
    decoded["id"] = workspace_id
    return decoded


@router.get("/workspaces/debug")
async def debug_workspace_storage(x_api_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Debug endpoint to diagnose workspace storage issues"""
    verify_token(x_api_token)
    
    try:
        # Test basic Valkey operations
        client = get_client()
        
        # Test 1: Basic SET/GET
        test_key = f"debug-test-{int(time.time())}"
        test_value = json.dumps({"test": True, "timestamp": time.time()})
        
        client.set(test_key, test_value)
        retrieved = client.get(test_key)
        client.delete(test_key)
        
        basic_test_passed = retrieved == test_value
        
        # Test 2: Hash operations
        hash_key = f"debug-hash-{int(time.time())}"
        hash_data = {"field1": "value1", "field2": "value2"}
        
        client.hset(hash_key, mapping=hash_data)
        hash_retrieved = client.hgetall(hash_key)
        client.delete(hash_key)
        
        hash_test_passed = len(hash_retrieved) == 2
        
        # Test 3: Workspace pattern
        workspace_id = f"debug-workspace-{int(time.time())}"
        workspace_key = f"workspaces:{workspace_id}:keys"
        workspace_data = {
            "provider": "openai",
            "openai_key": "sk-test",
            "gemini_key": "",
            "tavily_key": ""
        }
        
        client.hset(workspace_key, mapping=workspace_data)
        workspace_retrieved = client.hgetall(workspace_key)
        
        # Check all keys
        all_keys = client.keys("*")
        workspace_keys = client.keys("workspaces:*:keys")
        
        # Clean up
        client.delete(workspace_key)
        
        workspace_test_passed = len(workspace_retrieved) == 4
        
        return {
            "basic_set_get_test": {
                "passed": basic_test_passed,
                "expected": test_value,
                "got": retrieved
            },
            "hash_operations_test": {
                "passed": hash_test_passed,
                "expected_fields": 2,
                "got_fields": len(hash_retrieved)
            },
            "workspace_pattern_test": {
                "passed": workspace_test_passed,
                "expected_fields": 4,
                "got_fields": len(workspace_retrieved)
            },
            "key_analysis": {
                "total_keys": len(all_keys),
                "workspace_keys": len(workspace_keys),
                "all_keys_sample": [k.decode() if isinstance(k, bytes) else k for k in all_keys[:10]],
                "workspace_keys_sample": [k.decode() if isinstance(k, bytes) else k for k in workspace_keys[:5]]
            },
            "client_info": {
                "client_type": str(type(client)),
                "is_fake": hasattr(client, 'is_fake'),
                "valkey_url": os.getenv("VALKEY_URL", "Not set"),
                "render_service_id": os.getenv("RENDER_SERVICE_ID", "Not set")
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "client_info": {
                "valkey_url": os.getenv("VALKEY_URL", "Not set"),
                "render_service_id": os.getenv("RENDER_SERVICE_ID", "Not set")
            }
        }


@router.post("/workspaces")
async def add_workspace(payload: WorkspaceCreate, x_api_token: Optional[str] = Header(default=None)) -> Dict[str, str]:
    verify_token(x_api_token)
    workspace_id = payload.workspace_id or str(uuid.uuid4())
    mapping = {
        "provider": payload.keys.provider,
        "openai_key": payload.keys.openai_key or "",
        "gemini_key": payload.keys.gemini_key or "",
        "tavily_key": payload.keys.tavily_key or "",
    }
    
    try:
        # ALWAYS get fresh client for cross-container reliability
        client = get_client()
        
        # Store workspace data
        client.hset(f"workspaces:{workspace_id}:keys", mapping=mapping)
        
        # IMMEDIATELY verify storage with fresh connection
        verification_client = get_client()
        stored_data = verification_client.hgetall(f"workspaces:{workspace_id}:keys")
        
        if not stored_data:
            raise Exception("Workspace data not found after storage")
        
        # Verify the data matches what we stored
        decoded_stored = _decode_map(stored_data)
        if decoded_stored.get("provider") != mapping["provider"]:
            raise Exception("Stored data mismatch")
        
        print(f"SUCCESS: Stored and verified workspace {workspace_id}")
        return {"workspace_id": workspace_id}
        
    except Exception as e:
        print(f"ERROR storing workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store workspace: {e}")


@router.get("/workspaces")
async def list_workspaces(x_api_token: Optional[str] = Header(default=None)) -> Dict[str, List[Dict[str, Any]]]:
    verify_token(x_api_token)
    try:
        # ALWAYS get fresh client for cross-container reliability
        client = get_client()
        
        # Get all workspace keys
        workspace_keys = client.keys("workspaces:*:keys")
        
        print(f"DEBUG: Found {len(workspace_keys)} workspace keys")
        
        items: List[Dict[str, Any]] = []
        for key in workspace_keys:
            key_str = key.decode() if isinstance(key, (bytes, bytearray)) else key
            data = client.hgetall(key)
            
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
async def get_workspace_detail(workspace_id: str, x_api_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    verify_token(x_api_token)
    return get_workspace(workspace_id)


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, x_api_token: Optional[str] = Header(default=None)) -> Dict[str, str]:
    verify_token(x_api_token)
    try:
        # ALWAYS get fresh client for cross-container reliability
        client = get_client()
        
        # Check if workspace exists
        data = client.hgetall(f"workspaces:{workspace_id}:keys")
        if not data:
            raise HTTPException(status_code=404, detail="workspace not found")
        
        # Delete workspace
        client.delete(f"workspaces:{workspace_id}:keys")
        
        return {"message": f"Workspace {workspace_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR deleting workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete workspace: {e}")
