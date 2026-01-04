"""
Comprehensive workspace debugging and investigation tools.
Diagnoses the complete data flow from creation to listing.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.core.valkey import get_client
from backend.core.distributed_workspaces import distributed_workspace_manager


class WorkspaceInvestigator:
    """Comprehensive workspace debugging and investigation"""
    
    def __init__(self):
        self.investigation_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log investigation step"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] {level}: {message}"
        self.investigation_log.append(log_entry)
        print(log_entry)
    
    def investigate_valkey_connection(self) -> Dict[str, Any]:
        """Investigate Valkey connection and basic operations"""
        self.log("=== INVESTIGATING VALKEY CONNECTION ===")
        
        results = {}
        
        try:
            # Test 1: Basic connection
            self.log("Testing basic Valkey connection...")
            client = get_client()
            ping_result = client.ping()
            results['ping'] = {'success': ping_result, 'client_type': str(type(client))}
            self.log(f"Ping result: {ping_result}")
            
            # Test 2: Basic SET/GET
            self.log("Testing basic SET/GET operations...")
            test_key = f"investigation:setget:{int(time.time())}"
            test_value = json.dumps({"test": True, "timestamp": time.time()})
            
            set_result = client.set(test_key, test_value)
            get_result = client.get(test_key)
            delete_result = client.delete(test_key)
            
            results['setget'] = {
                'set_success': set_result,
                'get_result': get_result,
                'get_matches': get_result == test_value,
                'delete_success': delete_result
            }
            self.log(f"SET/GET test: set={set_result}, get_matches={get_result == test_value}")
            
            # Test 3: Hash operations
            self.log("Testing hash operations...")
            hash_key = f"investigation:hash:{int(time.time())}"
            hash_data = {"field1": "value1", "field2": "value2", "field3": "value3"}
            
            hset_result = client.hset(hash_key, mapping=hash_data)
            hgetall_result = client.hgetall(hash_key)
            hdel_result = client.delete(hash_key)
            
            results['hash'] = {
                'hset_success': hset_result,
                'hgetall_count': len(hgetall_result),
                'hgetall_data': {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in hgetall_result.items()},
                'delete_success': hdel_result
            }
            self.log(f"Hash test: hset={hset_result}, hgetall_count={len(hgetall_result)}")
            
            # Test 4: Key pattern matching
            self.log("Testing key pattern matching...")
            pattern_keys = client.keys("*")
            workspace_keys = client.keys("workspaces:*")
            
            results['patterns'] = {
                'total_keys': len(pattern_keys),
                'workspace_keys': len(workspace_keys),
                'sample_keys': [k.decode() if isinstance(k, bytes) else k for k in pattern_keys[:10]],
                'sample_workspace_keys': [k.decode() if isinstance(k, bytes) else k for k in workspace_keys[:5]]
            }
            self.log(f"Pattern test: total_keys={len(pattern_keys)}, workspace_keys={len(workspace_keys)}")
            
        except Exception as e:
            self.log(f"Valkey investigation failed: {e}", "ERROR")
            results['error'] = str(e)
        
        return results
    
    def investigate_workspace_creation(self) -> Dict[str, Any]:
        """Investigate workspace creation process"""
        self.log("=== INVESTIGATING WORKSPACE CREATION ===")
        
        results = {}
        test_workspace_id = f"investigation-{int(time.time())}"
        test_data = {
            "provider": "openai",
            "openai_key": "sk-investigation-test",
            "gemini_key": "",
            "tavily_key": ""
        }
        
        try:
            # Test 1: Direct Valkey storage
            self.log("Testing direct Valkey workspace storage...")
            client = get_client()
            workspace_key = f"workspaces:{test_workspace_id}:keys"
            
            direct_set_result = client.hset(workspace_key, mapping=test_data)
            direct_get_result = client.hgetall(workspace_key)
            
            results['direct_storage'] = {
                'set_success': direct_set_result,
                'get_result_count': len(direct_get_result),
                'get_result_data': {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in direct_get_result.items()},
                'workspace_key': workspace_key
            }
            self.log(f"Direct storage: set={direct_set_result}, get_count={len(direct_get_result)}")
            
            # Test 2: Distributed manager creation
            self.log("Testing distributed workspace manager creation...")
            distributed_workspace_id = f"investigation-distributed-{int(time.time())}"
            
            distributed_result = distributed_workspace_manager.create_workspace_distributed(
                distributed_workspace_id, test_data
            )
            
            results['distributed_creation'] = {
                'success': distributed_result.get('id') == distributed_workspace_id,
                'workspace_id': distributed_result.get('id'),
                'provider': distributed_result.get('provider'),
                'data': distributed_result
            }
            self.log(f"Distributed creation: success={distributed_result.get('id') == distributed_workspace_id}")
            
            # Test 3: Verify both workspaces exist
            self.log("Verifying both workspaces exist in Valkey...")
            all_workspace_keys = client.keys("workspaces:*:keys")
            
            found_direct = any(test_workspace_id.encode() in key for key in all_workspace_keys)
            found_distributed = any(distributed_workspace_id.encode() in key for key in all_workspace_keys)
            
            results['verification'] = {
                'total_workspace_keys': len(all_workspace_keys),
                'found_direct': found_direct,
                'found_distributed': found_distributed,
                'all_workspace_keys': [k.decode() if isinstance(k, bytes) else k for k in all_workspace_keys]
            }
            self.log(f"Verification: found_direct={found_direct}, found_distributed={found_distributed}")
            
            # Cleanup
            client.delete(f"workspaces:{test_workspace_id}:keys")
            client.delete(f"workspaces:{distributed_workspace_id}:keys")
            
        except Exception as e:
            self.log(f"Workspace creation investigation failed: {e}", "ERROR")
            results['error'] = str(e)
        
        return results
    
    def investigate_workspace_listing(self) -> Dict[str, Any]:
        """Investigate workspace listing process"""
        self.log("=== INVESTIGATING WORKSPACE LISTING ===")
        
        results = {}
        
        try:
            # Test 1: Direct Valkey listing
            self.log("Testing direct Valkey workspace listing...")
            client = get_client()
            workspace_keys = client.keys("workspaces:*:keys")
            
            direct_list = []
            for key in workspace_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                data = client.hgetall(key)
                
                if data:
                    parts = key_str.split(":")
                    workspace_id = parts[1] if len(parts) >= 3 else key_str
                    
                    decoded_data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
                    decoded_data["id"] = workspace_id
                    direct_list.append(decoded_data)
            
            results['direct_listing'] = {
                'keys_found': len(workspace_keys),
                'workspaces_returned': len(direct_list),
                'workspace_data': direct_list
            }
            self.log(f"Direct listing: keys={len(workspace_keys)}, workspaces={len(direct_list)}")
            
            # Test 2: Distributed manager listing
            self.log("Testing distributed workspace manager listing...")
            distributed_list = distributed_workspace_manager.list_workspaces_distributed()
            
            results['distributed_listing'] = {
                'workspaces_returned': len(distributed_list),
                'workspace_data': distributed_list
            }
            self.log(f"Distributed listing: workspaces={len(distributed_list)}")
            
            # Test 3: Compare results
            self.log("Comparing listing results...")
            comparison = {
                'direct_count': len(direct_list),
                'distributed_count': len(distributed_list),
                'counts_match': len(direct_list) == len(distributed_list),
                'data_match': len(direct_list) == len(distributed_list) and 
                             all(d.get('id') in [dd.get('id') for dd in distributed_list] for d in direct_list)
            }
            
            results['comparison'] = comparison
            self.log(f"Comparison: counts_match={comparison['counts_match']}, data_match={comparison['data_match']}")
            
        except Exception as e:
            self.log(f"Workspace listing investigation failed: {e}", "ERROR")
            results['error'] = str(e)
        
        return results
    
    def investigate_cross_container_consistency(self) -> Dict[str, Any]:
        """Investigate cross-container consistency issues"""
        self.log("=== INVESTIGATING CROSS-CONTAINER CONSISTENCY ===")
        
        results = {}
        
        try:
            # Test 1: Multiple fresh connections
            self.log("Testing multiple fresh connections...")
            connections = []
            for i in range(3):
                client = get_client()
                connections.append(client)
                self.log(f"Connection {i+1}: {type(client)}")
            
            # Test 2: Same data from different connections
            self.log("Testing data consistency across connections...")
            test_key = f"consistency-test-{int(time.time())}"
            test_value = json.dumps({"connection_test": True, "timestamp": time.time()})
            
            # Write with first connection
            connections[0].set(test_key, test_value)
            
            # Read with all connections
            read_results = []
            for i, client in enumerate(connections):
                result = client.get(test_key)
                read_results.append(result == test_value)
                self.log(f"Connection {i+1} read: {result == test_value}")
            
            # Cleanup
            connections[0].delete(test_key)
            
            results['connection_consistency'] = {
                'connections_tested': len(connections),
                'consistent_reads': all(read_results),
                'read_results': read_results
            }
            
            # Test 3: Workspace data across connections
            self.log("Testing workspace data across connections...")
            test_workspace_id = f"consistency-workspace-{int(time.time())}"
            test_workspace_data = {
                "provider": "openai",
                "openai_key": "sk-consistency-test",
                "gemini_key": "",
                "tavily_key": ""
            }
            
            # Create with first connection
            workspace_key = f"workspaces:{test_workspace_id}:keys"
            connections[0].hset(workspace_key, mapping=test_workspace_data)
            
            # Read with all connections
            workspace_read_results = []
            for i, client in enumerate(connections):
                data = client.hgetall(workspace_key)
                workspace_read_results.append(len(data) > 0)
                self.log(f"Connection {i+1} workspace read: {len(data) > 0}")
            
            # Cleanup
            connections[0].delete(workspace_key)
            
            results['workspace_consistency'] = {
                'connections_tested': len(connections),
                'consistent_workspace_reads': all(workspace_read_results),
                'workspace_read_results': workspace_read_results
            }
            
        except Exception as e:
            self.log(f"Cross-container consistency investigation failed: {e}", "ERROR")
            results['error'] = str(e)
        
        return results
    
    def investigate_environment_factors(self) -> Dict[str, Any]:
        """Investigate environmental factors"""
        self.log("=== INVESTIGATING ENVIRONMENTAL FACTORS ===")
        
        import os
        
        results = {
            'environment_variables': {
                'VALKEY_URL': os.getenv("VALKEY_URL", "Not set"),
                'VALKEY_HOST': os.getenv("VALKEY_HOST", "Not set"),
                'VALKEY_PORT': os.getenv("VALKEY_PORT", "Not set"),
                'RENDER_SERVICE_ID': os.getenv("RENDER_SERVICE_ID", "Not set"),
                'API_TOKEN': "Set" if os.getenv("API_TOKEN") else "Not set"
            },
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            'platform': os.sys.platform
        }
        
        self.log(f"Environment: VALKEY_URL={results['environment_variables']['VALKEY_URL']}")
        self.log(f"Environment: RENDER_SERVICE_ID={results['environment_variables']['RENDER_SERVICE_ID']}")
        
        return results
    
    def run_full_investigation(self) -> Dict[str, Any]:
        """Run complete investigation"""
        self.log("=== STARTING FULL WORKSPACE INVESTIGATION ===")
        
        investigation_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'valkey_connection': self.investigate_valkey_connection(),
            'workspace_creation': self.investigate_workspace_creation(),
            'workspace_listing': self.investigate_workspace_listing(),
            'cross_container_consistency': self.investigate_cross_container_consistency(),
            'environment_factors': self.investigate_environment_factors(),
            'investigation_log': self.investigation_log
        }
        
        self.log("=== INVESTIGATION COMPLETE ===")
        
        return investigation_results


# Global investigator instance
workspace_investigator = WorkspaceInvestigator()
