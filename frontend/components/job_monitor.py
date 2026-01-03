from __future__ import annotations

import json
from typing import Dict, List, Optional

import requests
import sseclient


def stream_job(api_url: str, job_id: str, timeout: int = 60, headers: Optional[Dict[str, str]] = None) -> List[Dict]:
    """
    Stream Server-Sent Events for a job until completion.
    Returns the list of received status payloads.
    """
    messages: List[Dict] = []
    with requests.get(f"{api_url}/stream/{job_id}", stream=True, timeout=timeout, headers=headers) as resp:
        resp.raise_for_status()
        client = sseclient.SSEClient(resp)
        for event in client.events():
            if event.data:
                payload = json.loads(event.data)
                messages.append(payload)
                if payload.get("status") in {"complete", "failed"}:
                    break
    return messages
