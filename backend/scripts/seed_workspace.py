#!/usr/bin/env python3
"""
Seed a demo workspace with BYOK (Bring Your Own Key) configuration.

Usage:
    API_URL=http://localhost:10000 \
    SEED_WORKSPACE_ID=demo-workspace \
    SEED_PROVIDER=openai \
    OPENAI_KEY="sk-..." \
    GEMINI_KEY="..." \
    TAVILY_KEY="..." \
    python backend/scripts/seed_workspace.py
"""
from __future__ import annotations

import os
import sys
import httpx


def main() -> None:
    api_url = os.environ.get("API_URL", "http://localhost:10000")
    workspace_id = os.environ.get("SEED_WORKSPACE_ID", "demo-workspace")
    provider = os.environ.get("SEED_PROVIDER", "openai")
    openai_key = os.environ.get("OPENAI_KEY", "")
    gemini_key = os.environ.get("GEMINI_KEY", "")
    tavily_key = os.environ.get("TAVILY_KEY", "")

    if not openai_key and not gemini_key:
        print("ERROR: At least one of OPENAI_KEY or GEMINI_KEY must be provided", file=sys.stderr)
        sys.exit(1)

    if provider not in {"openai", "gemini"}:
        print(f"ERROR: SEED_PROVIDER must be 'openai' or 'gemini', got '{provider}'", file=sys.stderr)
        sys.exit(1)

    payload = {
        "workspace_id": workspace_id,
        "provider": provider,
        "keys": {
            "openai_key": openai_key,
            "gemini_key": gemini_key,
            "tavily_key": tavily_key,
        },
    }

    print(f"Seeding workspace '{workspace_id}' with provider '{provider}'...")
    print(f"API URL: {api_url}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{api_url}/workspaces", json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"✓ Workspace created successfully: {result}")
            print(f"✓ Workspace ID: {result.get('workspace_id')}")
    except httpx.HTTPStatusError as e:
        print(f"ERROR: HTTP {e.response.status_code} - {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"ERROR: Failed to connect to {api_url} - {e}", file=sys.stderr)
        print("Make sure the API server is running.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
