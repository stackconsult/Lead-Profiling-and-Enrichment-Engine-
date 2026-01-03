"""
Seed a workspace from environment variables (BYOK demo).

Env:
- API_URL (default: http://localhost:10000)
- API_TOKEN (optional)
- SEED_WORKSPACE_ID (default: demo-workspace)
- SEED_PROVIDER (openai|gemini, default: openai)
- OPENAI_KEY (required if provider=openai)
- GEMINI_KEY (required if provider=gemini)
- TAVILY_KEY (optional)
"""
from __future__ import annotations

import os
import sys

import httpx


def main() -> None:
    api_url = os.getenv("API_URL", "http://localhost:10000").rstrip("/")
    api_token = os.getenv("API_TOKEN")
    workspace_id = os.getenv("SEED_WORKSPACE_ID", "demo-workspace")
    provider = os.getenv("SEED_PROVIDER", "openai")

    if provider not in {"openai", "gemini"}:
        sys.exit("SEED_PROVIDER must be 'openai' or 'gemini'")

    openai_key = os.getenv("OPENAI_KEY", "")
    gemini_key = os.getenv("GEMINI_KEY", "")
    tavily_key = os.getenv("TAVILY_KEY", "")

    if provider == "openai" and not openai_key:
        sys.exit("OPENAI_KEY is required for provider=openai")
    if provider == "gemini" and not gemini_key:
        sys.exit("GEMINI_KEY is required for provider=gemini")

    payload = {
        "provider": provider,
        "workspace_id": workspace_id,
        "keys": {
            "openai_key": openai_key,
            "gemini_key": gemini_key,
            "tavily_key": tavily_key,
        },
    }

    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["X-API-TOKEN"] = api_token

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(f"{api_url}/workspaces", json=payload, headers=headers)
    if resp.is_success:
        print(f"Seeded workspace '{workspace_id}' (provider={provider})")
    else:
        sys.exit(f"Failed to seed workspace: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    main()
