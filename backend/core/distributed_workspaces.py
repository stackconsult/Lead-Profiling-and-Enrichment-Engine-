"""
Distributed workspace manager with proper consistency guarantees.
Solves cross-container data persistence issues in distributed environments.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import redis
from redis.connection import ConnectionPool

from backend.core.valkey import get_client


@dataclass
class WorkspaceOperation:
    """Represents a workspace operation with metadata"""
    operation_id: str
    operation_type: str  # 'create', 'read', 'update', 'delete'
    workspace_id: str
    data: Dict[str, Any]
    timestamp: datetime
    status: str = 'pending'  # 'pending', 'completed', 'failed'
    error: Optional[str] = None


class DistributedWorkspaceManager:
    """
    Manages workspace operations with distributed consistency guarantees.
    Uses Redis-based locking and operation queuing for cross-container reliability.
    """
    
    def __init__(self):
        # DO NOT initialize client at import time - this causes startup failures
        self.client = None
        self.lock_timeout = 10  # 10 seconds
        self.operation_timeout = 30  # 30 seconds
    
    def _get_client(self):
        """Get fresh client when needed, not at import time"""
        if self.client is None:
            self.client = get_client()
        return self.client
    
    def _acquire_lock(self, resource: str, timeout: int = None) -> Optional[str]:
        """Acquire distributed lock using Redis SET NX EX"""
        if timeout is None:
            timeout = self.lock_timeout
        
        lock_key = f"locks:{resource}"
        lock_value = str(uuid.uuid4())
        
        # Try to acquire lock with expiration
        client = self._get_client()
        result = client.set(lock_key, lock_value, nx=True, ex=timeout)
        
        if result:
            return lock_value
        return None
    
    def _release_lock(self, resource: str, lock_value: str) -> bool:
        """Release distributed lock using Lua script for atomicity"""
        lock_key = f"locks:{resource}"
        client = self._get_client()
        
        # Lua script to atomically release lock if we own it
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = client.eval(lua_script, 1, lock_key, lock_value)
        return result == 1
    
    def _queue_operation(self, operation: WorkspaceOperation) -> str:
        """Queue operation for distributed processing"""
        client = self._get_client()
        operation_key = f"operations:{operation.operation_id}"
        queue_key = "workspace_operations_queue"
        
        # Store operation details
        operation_data = {
            "operation_id": operation.operation_id,
            "operation_type": operation.operation_type,
            "workspace_id": operation.workspace_id,
            "data": json.dumps(operation.data),
            "timestamp": operation.timestamp.isoformat(),
            "status": operation.status,
            "error": operation.error or ""
        }
        
        # Store operation details
        client.hset(operation_key, mapping=operation_data)
        client.expire(operation_key, self.operation_timeout)
        
        # Add to queue
        client.lpush(queue_key, operation.operation_id)
        
        return operation.operation_id
    
    def _get_operation_result(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get operation result"""
        client = self._get_client()
        operation_key = f"operations:{operation_id}"
        data = client.hgetall(operation_key)
        
        if not data:
            return None
        
        return {
            "operation_id": operation_id,
            "operation_type": data.get(b"operation_type", b"").decode(),
            "workspace_id": data.get(b"workspace_id", b"").decode(),
            "data": json.loads(data.get(b"data", b"{}").decode()),
            "timestamp": data.get(b"timestamp", b"").decode(),
            "status": data.get(b"status", b"").decode(),
            "error": data.get(b"error", b"").decode()
        }
    
    def create_workspace_distributed(self, workspace_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create workspace with distributed consistency guarantees"""
        operation_id = str(uuid.uuid4())
        operation = WorkspaceOperation(
            operation_id=operation_id,
            operation_type="create",
            workspace_id=workspace_id,
            data=data,
            timestamp=datetime.utcnow()
        )
        
        # Queue the operation
        self._queue_operation(operation)
        
        # Process the operation with locking
        return self._process_create_operation(operation)
    
    def _process_create_operation(self, operation: WorkspaceOperation) -> Dict[str, Any]:
        """Process create operation with distributed locking"""
        workspace_key = f"workspaces:{operation.workspace_id}:keys"
        lock_key = f"workspace_create:{operation.workspace_id}"
        
        # Try to acquire lock
        lock_value = self._acquire_lock(lock_key)
        if not lock_value:
            # If we can't acquire lock, wait and retry
            time.sleep(0.1)
            lock_value = self._acquire_lock(lock_key)
            if not lock_value:
                raise Exception(f"Could not acquire lock for workspace {operation.workspace_id}")
        
        try:
            # Check if workspace already exists
            client = self._get_client()
            existing_data = client.hgetall(workspace_key)
            if existing_data:
                # Workspace already exists, return existing data
                decoded_data = self._decode_map(existing_data)
                decoded_data["id"] = operation.workspace_id
                return decoded_data
            
            # Store workspace data
            client.hset(workspace_key, mapping=operation.data)
            
            # Verify storage
            stored_data = client.hgetall(workspace_key)
            if not stored_data:
                raise Exception("Workspace data not found after storage")
            
            # Update operation status
            operation_key = f"operations:{operation.operation_id}"
            client.hset(operation_key, "status", "completed")
            
            # Return success
            decoded_data = self._decode_map(stored_data)
            decoded_data["id"] = operation.workspace_id
            return decoded_data
            
        except Exception as e:
            # Update operation status to failed
            client = self._get_client()
            operation_key = f"operations:{operation.operation_id}"
            client.hset(operation_key, "status", "failed")
            client.hset(operation_key, "error", str(e))
            raise
        
        finally:
            # Always release the lock
            self._release_lock(lock_key, lock_value)
    
    def list_workspaces_distributed(self) -> List[Dict[str, Any]]:
        """List workspaces with distributed consistency"""
        # Use distributed lock for listing operation
        lock_key = "workspace_list_operation"
        lock_value = self._acquire_lock(lock_key, timeout=5)
        
        if not lock_value:
            # If we can't get lock, try without it (read operation)
            return self._list_workspaces_without_lock()
        
        try:
            return self._list_workspaces_without_lock()
        finally:
            self._release_lock(lock_key, lock_value)
    
    def _list_workspaces_without_lock(self) -> List[Dict[str, Any]]:
        """List workspaces without distributed lock"""
        # Get all workspace keys with fresh connection
        fresh_client = get_client()
        workspace_keys = fresh_client.keys("workspaces:*:keys")
        
        items: List[Dict[str, Any]] = []
        for key in workspace_keys:
            key_str = key.decode() if isinstance(key, (bytes, bytearray)) else key
            data = fresh_client.hgetall(key)
            
            if data:
                # Extract workspace_id from "workspaces:{workspace_id}:keys"
                parts = key_str.split(":")
                workspace_id = parts[1] if len(parts) >= 3 else key_str
                
                decoded_data = self._decode_map(data)
                decoded_data["id"] = workspace_id
                items.append(decoded_data)
        
        return items
    
    def _decode_map(self, data: Dict[bytes, bytes]) -> Dict[str, str]:
        """Decode Redis map data"""
        return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    
    def get_workspace_distributed(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace with distributed consistency"""
        workspace_key = f"workspaces:{workspace_id}:keys"
        
        # Use fresh client for read operation
        fresh_client = get_client()
        data = fresh_client.hgetall(workspace_key)
        
        if not data:
            raise Exception(f"Workspace {workspace_id} not found")
        
        decoded_data = self._decode_map(data)
        decoded_data["id"] = workspace_id
        return decoded_data
    
    def delete_workspace_distributed(self, workspace_id: str) -> bool:
        """Delete workspace with distributed consistency"""
        workspace_key = f"workspaces:{workspace_id}:keys"
        lock_key = f"workspace_delete:{workspace_id}"
        
        # Acquire lock
        lock_value = self._acquire_lock(lock_key)
        if not lock_value:
            raise Exception(f"Could not acquire lock for workspace deletion {workspace_id}")
        
        try:
            # Check if workspace exists
            fresh_client = get_client()
            data = fresh_client.hgetall(workspace_key)
            if not data:
                raise Exception(f"Workspace {workspace_id} not found")
            
            # Delete workspace
            fresh_client.delete(workspace_key)
            return True
            
        finally:
            self._release_lock(lock_key, lock_value)
    
    def cleanup_expired_operations(self) -> int:
        """Clean up expired operations"""
        client = self._get_client()
        pattern = "operations:*"
        keys = client.keys(pattern)
        
        cleaned = 0
        for key in keys:
            ttl = client.ttl(key)
            if ttl == -1:  # No expiration set
                client.expire(key, self.operation_timeout)
            elif ttl == -2:  # Key doesn't exist
                cleaned += 1
        
        return cleaned


# Global distributed workspace manager instance
distributed_workspace_manager = DistributedWorkspaceManager()
