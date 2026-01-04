"""
Targeted fix for workspace listing key pattern matching issue.
"""
from __future__ import annotations

import json
import time
from typing import Dict, List, Any, Optional

from backend.core.valkey import get_client


class WorkspaceListingFix:
    """Targeted fix for workspace listing issues"""
    
    def __init__(self):
        self.client = get_client()
    
    def investigate_key_patterns(self) -> Dict[str, Any]:
        """Investigate actual key patterns in Valkey"""
        print("=== INVESTIGATING KEY PATTERNS ===")
        
        # Get all keys
        all_keys = self.client.keys("*")
        print(f"Total keys found: {len(all_keys)}")
        
        # Decode all keys
        decoded_keys = []
        for key in all_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            decoded_keys.append(key_str)
        
        print(f"All keys: {decoded_keys}")
        
        # Find workspace-related keys
        workspace_keys = []
        for key_str in decoded_keys:
            if 'workspace' in key_str.lower():
                workspace_keys.append(key_str)
        
        print(f"Workspace-related keys: {workspace_keys}")
        
        # Test different patterns
        patterns = [
            "workspaces:*:keys",
            "workspaces:*",
            "*workspace*",
            "*:*:*",
            "*"
        ]
        
        pattern_results = {}
        for pattern in patterns:
            try:
                pattern_keys = self.client.keys(pattern)
                pattern_results[pattern] = {
                    'count': len(pattern_keys),
                    'keys': [k.decode() if isinstance(k, bytes) else k for k in pattern_keys]
                }
                print(f"Pattern '{pattern}': {len(pattern_keys)} keys")
            except Exception as e:
                pattern_results[pattern] = {'error': str(e)}
                print(f"Pattern '{pattern}' error: {e}")
        
        return {
            'total_keys': len(all_keys),
            'all_keys': decoded_keys,
            'workspace_keys': workspace_keys,
            'pattern_results': pattern_results
        }
    
    def fix_workspace_listing(self) -> List[Dict[str, Any]]:
        """Fixed workspace listing method"""
        print("=== FIXED WORKSPACE LISTING ===")
        
        # Try multiple approaches to find workspaces
        approaches = [
            # Approach 1: Original pattern
            lambda: self._list_by_pattern("workspaces:*:keys"),
            # Approach 2: Broader pattern
            lambda: self._list_by_pattern("workspaces:*"),
            # Approach 3: Workspace substring
            lambda: self._list_by_pattern("*workspace*"),
            # Approach 4: All keys and filter
            lambda: self._list_all_and_filter(),
        ]
        
        for i, approach in enumerate(approaches):
            try:
                print(f"Approach {i+1}: Trying...")
                result = approach()
                if result:
                    print(f"Approach {i+1} SUCCESS: Found {len(result)} workspaces")
                    return result
                else:
                    print(f"Approach {i+1}: No workspaces found")
            except Exception as e:
                print(f"Approach {i+1} ERROR: {e}")
        
        return []
    
    def _list_by_pattern(self, pattern: str) -> List[Dict[str, Any]]:
        """List workspaces by key pattern"""
        client = get_client()
        keys = client.keys(pattern)
        
        workspaces = []
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            data = client.hgetall(key)
            
            if data:
                # Extract workspace ID
                parts = key_str.split(":")
                workspace_id = parts[1] if len(parts) >= 3 else key_str
                
                decoded_data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
                decoded_data["id"] = workspace_id
                workspaces.append(decoded_data)
        
        return workspaces
    
    def _list_all_and_filter(self) -> List[Dict[str, Any]]:
        """List all keys and filter for workspaces"""
        client = get_client()
        all_keys = client.keys("*")
        
        workspaces = []
        for key in all_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            
            # Filter for workspace-related keys
            if 'workspace' in key_str.lower() or 'workspaces' in key_str.lower():
                data = client.hgetall(key)
                
                if data:
                    # Extract workspace ID
                    parts = key_str.split(":")
                    workspace_id = parts[1] if len(parts) >= 3 else key_str
                    
                    decoded_data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
                    decoded_data["id"] = workspace_id
                    workspaces.append(decoded_data)
        
        return workspaces


# Global fix instance
workspace_listing_fix = WorkspaceListingFix()
