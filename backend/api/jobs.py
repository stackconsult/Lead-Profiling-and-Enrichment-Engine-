from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from rq import Queue

from backend.api.workspaces import get_workspace
from backend.core.valkey import set_job_status, valkey_client
from backend.worker import process_lead

router = APIRouter(prefix="", tags=["jobs"])


class LeadPayload(BaseModel):
    company: Optional[str] = Field(default=None, description="Company name")
    name: Optional[str] = None
    id: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


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
async def enqueue(
    leads: List[LeadPayload],
    workspace_id: str = Query(..., description="Workspace ID referencing stored keys"),
) -> Dict[str, str]:
    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided")

    workspace = get_workspace(workspace_id)
    job_id = str(uuid.uuid4())
    set_job_status(job_id, "queued", progress=0.0)
    valkey_client.hset(f"jobs:{job_id}", mapping={"workspace_id": workspace_id, "provider": workspace.get("provider", "")})
    queue = _maybe_queue()

    if queue:
        for lead in leads:
            queue.enqueue(process_lead, lead.model_dump(), job_id, workspace)
    else:
        # Fallback to inline processing (tests, local dev without Valkey)
        for lead in leads:
            process_lead(lead.model_dump(), job_id, workspace)

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
    import asyncio

    async def event_generator():
        pubsub = valkey_client.pubsub()
        channel = f"jobs:{job_id}:events"
        try:
            pubsub.subscribe(channel)
            # First emit current state if any
            data = valkey_client.hgetall(f"jobs:{job_id}")
            if data:
                yield f"data: {json.dumps(_decode_map(data))}\n\n"
                status = data.get("status")
                if status in {b"complete", b"failed", "complete", "failed"}:
                    return
            # Then listen for updates
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    payload = message.get("data")
                    if isinstance(payload, (bytes, bytearray)):
                        payload = payload.decode()
                    if payload:
                        yield f"data: {payload}\n\n"
                        try:
                            parsed = json.loads(payload)
                            status = parsed.get("status")
                            if status in {"complete", "failed"}:
                                break
                        except Exception:
                            pass
                await asyncio.sleep(0.2)
        finally:
            try:
                pubsub.close()
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
