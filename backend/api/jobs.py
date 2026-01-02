from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from rq import Queue

from backend.core.valkey import set_job_status, valkey_client
from backend.worker import process_lead

router = APIRouter(prefix="", tags=["jobs"])


def _maybe_queue() -> Queue | None:
    if getattr(valkey_client, "is_fake", False):
        return None
    try:
        return Queue(connection=valkey_client)  # type: ignore[arg-type]
    except Exception:
        return None


def _decode_map(data: Dict[Any, Any]) -> Dict[str, Any]:
    def _decode(value: Any) -> Any:
        if isinstance(value, bytes):
            return value.decode()
        return value

    return {(_decode(k)): _decode(v) for k, v in data.items()}


@router.post("/enqueue")
async def enqueue(leads: List[Dict[str, Any]], workspace_id: str | None = None) -> Dict[str, str]:
    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided")

    job_id = str(uuid.uuid4())
    set_job_status(job_id, "queued", progress=0.0)
    queue = _maybe_queue()

    if queue:
        for lead in leads:
            queue.enqueue(process_lead, lead, job_id, workspace_id)
    else:
        # Fallback to inline processing (tests, local dev without Valkey)
        for lead in leads:
            process_lead(lead, job_id, workspace_id)

    return {"job_id": job_id}


@router.get("/status/{job_id}")
async def status(job_id: str) -> Dict[str, Any]:
    data = valkey_client.hgetall(f"jobs:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="job not found")
    return _decode_map(data)


@router.get("/leads")
async def leads(page: int = 1, size: int = 50) -> Dict[str, Any]:
    start = (page - 1) * size
    end = start + size - 1
    raw_keys = valkey_client.keys("leads:*")
    keys = [
        k.decode() if isinstance(k, (bytes, bytearray)) else k  # type: ignore[union-attr]
        for k in raw_keys
    ]
    keys = list(dict.fromkeys(keys))  # preserve order, drop dupes
    sliced = keys[start : end + 1]

    items: List[Dict[str, Any]] = []
    for key in sliced:
        data = valkey_client.hgetall(key)
        if data:
            items.append(_decode_map(data))

    return {"items": items, "page": page, "size": size, "total": len(keys)}


@router.get("/stream/{job_id}")
async def stream(job_id: str):
    from sse_starlette.sse import EventSourceResponse
    import asyncio

    async def event_generator():
        for _ in range(120):  # up to ~60s if 0.5s sleep
            data = valkey_client.hgetall(f"jobs:{job_id}")
            if data:
                yield {"event": "message", "data": json.dumps(_decode_map(data))}
                status = data.get("status") if isinstance(data, dict) else None
                if status in {b"complete", b"failed", "complete", "failed"}:
                    break
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())
