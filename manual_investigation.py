#!/usr/bin/env python3
"""
Manual investigation script to debug workspace listing issue.
"""
import requests
import json
import time

def manual_investigation():
    """Manually investigate the workspace listing issue"""
    base_url = "https://lead-profiling-and-enrichment-engine.onrender.com"
    headers = {"X-API-TOKEN": "test-token-123"}
    
    print("=== MANUAL WORKSPACE INVESTIGATION ===")
    
    # Step 1: Check health
    print("\n1. Checking API health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"   Health status: {response.status_code}")
        print(f"   Health response: {response.json()}")
    except Exception as e:
        print(f"   Health check failed: {e}")
        return
    
    # Step 2: Create a test workspace
    print("\n2. Creating test workspace...")
    test_workspace_id = f"manual-test-{int(time.time())}"
    workspace_data = {
        "provider": "openai",
        "workspace_id": test_workspace_id,
        "keys": {
            "provider": "openai",
            "openai_key": "sk-manual-test",
            "gemini_key": "",
            "tavily_key": ""
        }
    }
    
    try:
        response = requests.post(f"{base_url}/api/workspaces", json=workspace_data, headers=headers, timeout=10)
        print(f"   Creation status: {response.status_code}")
        print(f"   Creation response: {response.json()}")
    except Exception as e:
        print(f"   Creation failed: {e}")
        return
    
    # Step 3: List workspaces immediately
    print("\n3. Listing workspaces immediately after creation...")
    try:
        response = requests.get(f"{base_url}/api/workspaces", headers=headers, timeout=10)
        print(f"   Listing status: {response.status_code}")
        listing_data = response.json()
        print(f"   Workspaces found: {len(listing_data.get('items', []))}")
        print(f"   Workspace items: {listing_data.get('items', [])}")
    except Exception as e:
        print(f"   Listing failed: {e}")
    
    # Step 4: Wait and list again
    print("\n4. Waiting 5 seconds and listing again...")
    time.sleep(5)
    try:
        response = requests.get(f"{base_url}/api/workspaces", headers=headers, timeout=10)
        print(f"   Listing status: {response.status_code}")
        listing_data = response.json()
        print(f"   Workspaces found: {len(listing_data.get('items', []))}")
        print(f"   Workspace items: {listing_data.get('items', [])}")
    except Exception as e:
        print(f"   Listing failed: {e}")
    
    # Step 5: Try to get the specific workspace
    print(f"\n5. Getting specific workspace {test_workspace_id}...")
    try:
        response = requests.get(f"{base_url}/api/workspaces/{test_workspace_id}", headers=headers, timeout=10)
        print(f"   Get status: {response.status_code}")
        print(f"   Get response: {response.json()}")
    except Exception as e:
        print(f"   Get failed: {e}")
    
    print("\n=== INVESTIGATION COMPLETE ===")

if __name__ == "__main__":
    manual_investigation()
