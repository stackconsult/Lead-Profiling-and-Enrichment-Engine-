#!/usr/bin/env python3
"""
Simple health check for CI/CD workflows.
"""
import requests
import sys
import time


def simple_health_check(api_url: str, api_token: str = None):
    """Simple health check without complex imports"""
    print(f"🏥 Running simple health check against {api_url}")
    
    headers = {}
    if api_token:
        headers["X-API-TOKEN"] = api_token
    
    # Test basic health endpoint
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Basic health check passed")
        else:
            print(f"❌ Basic health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Basic health check error: {e}")
        return False
    
    # Test workspace endpoint
    try:
        response = requests.get(f"{api_url}/api/workspaces", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Workspace endpoint accessible")
            data = response.json()
            print(f"   Found {len(data.get('items', []))} workspaces")
        else:
            print(f"❌ Workspace endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Workspace endpoint error: {e}")
        return False
    
    # Test workspace creation
    try:
        test_workspace = {
            "provider": "openai",
            "workspace_id": f"health-check-{int(time.time())}",
            "keys": {
                "provider": "openai",
                "openai_key": "sk-test",
                "gemini_key": "",
                "tavily_key": ""
            }
        }
        
        response = requests.post(f"{api_url}/api/workspaces", json=test_workspace, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Workspace creation successful")
            result = response.json()
            workspace_id = result.get("workspace_id")
            
            # Test retrieval
            response = requests.get(f"{api_url}/api/workspaces", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                workspaces = data.get("items", [])
                found = any(w.get("id") == workspace_id for w in workspaces)
                if found:
                    print("✅ Workspace retrieval successful")
                else:
                    print("❌ Created workspace not found in list")
                    return False
            else:
                print("❌ Workspace retrieval failed")
                return False
        else:
            print(f"❌ Workspace creation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Workspace creation error: {e}")
        return False
    
    print("✅ All health checks passed!")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple health check")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--api-token", help="API token")
    
    args = parser.parse_args()
    
    success = simple_health_check(args.api_url, args.api_token)
    sys.exit(0 if success else 1)
