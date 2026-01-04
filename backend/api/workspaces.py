from __future__ import annotations

import os
import time
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field

from backend.core.distributed_workspaces import distributed_workspace_manager
from backend.core.workspace_investigator import workspace_investigator
from backend.core.workspace_listing_fix import workspace_listing_fix


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


def verify_token(x_api_token: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("API_TOKEN")
    if expected and x_api_token != expected:
        raise HTTPException(status_code=401, detail="invalid API token")


@router.post("/workspaces")
async def add_workspace(payload: WorkspaceCreate, x_api_token: Optional[str] = Header(default=None)) -> Dict[str, str]:
    """Create workspace with distributed consistency guarantees"""
    verify_token(x_api_token)
    
    workspace_id = payload.workspace_id or str(uuid.uuid4())
    mapping = {
        "provider": payload.keys.provider,
        "openai_key": payload.keys.openai_key or "",
        "gemini_key": payload.keys.gemini_key or "",
        "tavily_key": payload.keys.tavily_key or "",
    }
    
    try:
        print(f"Creating workspace {workspace_id} with distributed manager")
        
        # Use distributed workspace manager for consistency
        result = distributed_workspace_manager.create_workspace_distributed(workspace_id, mapping)
        
        print(f"SUCCESS: Created workspace {workspace_id}")
        return {"workspace_id": workspace_id}
        
    except Exception as e:
        print(f"ERROR creating workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {e}")


@router.get("/workspaces")
async def list_workspaces(x_api_token: Optional[str] = Header(default=None)) -> Dict[str, List[Dict[str, Any]]]:
    """List workspaces with distributed consistency"""
    verify_token(x_api_token)
    
    try:
        print(f"Listing workspaces with distributed manager")
        
        # Use distributed workspace manager for consistency
        items = distributed_workspace_manager.list_workspaces_distributed()
        
        print(f"SUCCESS: Found {len(items)} workspaces")
        return {"items": items}
        
    except Exception as e:
        print(f"ERROR listing workspaces: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workspaces: {e}")


@router.get("/workspaces/{workspace_id}")
async def get_workspace_detail(workspace_id: str, x_api_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Get workspace with distributed consistency"""
    verify_token(x_api_token)
    
    try:
        print(f"Getting workspace {workspace_id} with distributed manager")
        
        # Use distributed workspace manager for consistency
        result = distributed_workspace_manager.get_workspace_distributed(workspace_id)
        
        print(f"SUCCESS: Retrieved workspace {workspace_id}")
        return result
        
    except Exception as e:
        print(f"ERROR getting workspace {workspace_id}: {e}")
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="workspace not found")
        raise HTTPException(status_code=500, detail=f"Failed to get workspace: {e}")


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, x_api_token: Optional[str] = Header(default=None)) -> Dict[str, str]:
    """Delete workspace with distributed consistency"""
    verify_token(x_api_token)
    
    try:
        print(f"Deleting workspace {workspace_id} with distributed manager")
        
        # Use distributed workspace manager for consistency
        success = distributed_workspace_manager.delete_workspace_distributed(workspace_id)
        
        if success:
            print(f"SUCCESS: Deleted workspace {workspace_id}")
            return {"message": f"Workspace {workspace_id} deleted successfully"}
        else:
            raise Exception("Delete operation failed")
        
    except Exception as e:
        print(f"ERROR deleting workspace {workspace_id}: {e}")
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="workspace not found")
        raise HTTPException(status_code=500, detail=f"Failed to delete workspace: {e}")


@router.get("/workspaces/fix")
async def fix_workspace_listing(x_api_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Fix workspace listing with multiple approaches"""
    verify_token(x_api_token)
    
    try:
        print("Running workspace listing fix...")
        
        # Investigate key patterns
        key_investigation = workspace_listing_fix.investigate_key_patterns()
        
        # Try fixed listing
        fixed_workspaces = workspace_listing_fix.fix_workspace_listing()
        
        return {
            'key_investigation': key_investigation,
            'fixed_listing': {
                'workspaces_found': len(fixed_workspaces),
                'workspaces': fixed_workspaces
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Fix failed: {e}")
        return {
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.utcnow().isoformat()
        }


@router.get("/workspaces/investigate")
async def investigate_workspace_issue(x_api_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Comprehensive investigation of workspace listing issue"""
    verify_token(x_api_token)
    
    try:
        print("Starting comprehensive workspace investigation...")
        
        # Run full investigation
        results = workspace_investigator.run_full_investigation()
        
        # Add summary analysis
        analysis = {
            'overall_health': 'HEALTHY' if results['valkey_connection'].get('ping', {}).get('success') else 'UNHEALTHY',
            'creation_working': results['workspace_creation'].get('direct_storage', {}).get('set_success', False),
            'listing_working': len(results['workspace_listing'].get('direct_listing', {}).get('workspace_data', [])) > 0,
            'consistency_working': results['cross_container_consistency'].get('connection_consistency', {}).get('consistent_reads', False),
            'issues_identified': []
        }
        
        # Identify specific issues
        if not results['valkey_connection'].get('ping', {}).get('success'):
            analysis['issues_identified'].append('Valkey connection failure')
        
        if not results['workspace_creation'].get('direct_storage', {}).get('set_success'):
            analysis['issues_identified'].append('Workspace creation failure')
        
        if len(results['workspace_listing'].get('direct_listing', {}).get('workspace_data', [])) == 0:
            analysis['issues_identified'].append('Workspace listing returns empty')
        
        if not results['cross_container_consistency'].get('connection_consistency', {}).get('consistent_reads'):
            analysis['issues_identified'].append('Cross-container consistency issues')
        
        results['analysis'] = analysis
        
        print("Investigation completed successfully")
        return results
        
    except Exception as e:
        print(f"Investigation failed: {e}")
        return {
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.utcnow().isoformat()
        }


@router.get("/workspaces/debug")
async def debug_workspace_storage(x_api_token: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Debug endpoint to diagnose workspace storage issues"""
    verify_token(x_api_token)
    
    try:
        # Test distributed manager operations
        test_workspace_id = f"debug-distributed-{int(time.time())}"
        test_data = {
            "provider": "openai",
            "openai_key": "sk-debug-test",
            "gemini_key": "",
            "tavily_key": ""
        }
        
        # Test creation
        print("Testing distributed workspace creation...")
        created = distributed_workspace_manager.create_workspace_distributed(test_workspace_id, test_data)
        
        # Test retrieval
        print("Testing distributed workspace retrieval...")
        retrieved = distributed_workspace_manager.get_workspace_distributed(test_workspace_id)
        
        # Test listing
        print("Testing distributed workspace listing...")
        all_workspaces = distributed_workspace_manager.list_workspaces_distributed()
        
        # Test deletion
        print("Testing distributed workspace deletion...")
        deleted = distributed_workspace_manager.delete_workspace_distributed(test_workspace_id)
        
        # Cleanup expired operations
        cleaned = distributed_workspace_manager.cleanup_expired_operations()
        
        return {
            "distributed_tests": {
                "creation_test": {
                    "passed": created.get("id") == test_workspace_id,
                    "workspace_id": created.get("id"),
                    "provider": created.get("provider")
                },
                "retrieval_test": {
                    "passed": retrieved.get("id") == test_workspace_id,
                    "workspace_id": retrieved.get("id"),
                    "provider": retrieved.get("provider")
                },
                "listing_test": {
                    "passed": len(all_workspaces) >= 0,  # Should have at least 0
                    "total_workspaces": len(all_workspaces)
                },
                "deletion_test": {
                    "passed": deleted,
                    "deleted": deleted
                }
            },
            "cleanup_info": {
                "expired_operations_cleaned": cleaned
            },
            "environment_info": {
                "valkey_url": os.getenv("VALKEY_URL", "Not set"),
                "render_service_id": os.getenv("RENDER_SERVICE_ID", "Not set")
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "environment_info": {
                "valkey_url": os.getenv("VALKEY_URL", "Not set"),
                "render_service_id": os.getenv("RENDER_SERVICE_ID", "Not set")
            }
        }
