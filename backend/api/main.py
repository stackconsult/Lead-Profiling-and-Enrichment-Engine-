from __future__ import annotations

from typing import Dict, Optional
import json
import asyncio

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.api import jobs, workspaces
from backend.core.valkey import valkey_client

app = FastAPI(title="ProspectPulse API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_token(x_api_token: Optional[str] = Header(default=None)) -> None:
    import os

    expected = os.getenv("API_TOKEN")
    if expected and x_api_token != expected:
        raise HTTPException(status_code=401, detail="invalid API token")


@app.get("/health")
async def health() -> Dict[str, str]:
    try:
        valkey_client.ping()
    except Exception as exc:
        return {"status": "degraded", "detail": str(exc)}
    return {"status": "ok"}


@app.get("/stream/{job_id}")
async def stream_job_updates(job_id: str):
    """Server-Sent Events endpoint for real-time job updates"""
    
    async def event_stream():
        last_status = None
        while True:
            try:
                # Get job status from Valkey
                job_data = valkey_client.get(f"jobs:{job_id}")
                if not job_data:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                    break
                
                job = json.loads(job_data)
                current_status = job.get('status')
                
                # Only send update if status changed
                if current_status != last_status:
                    yield f"data: {json.dumps(job)}\n\n"
                    last_status = current_status
                
                # Stop streaming if job is complete
                if current_status in ['completed', 'failed']:
                    break
                
                await asyncio.sleep(1)
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return StreamingResponse(event_stream(), media_type="text/plain")


app.include_router(jobs.router, dependencies=[Depends(verify_token)])
app.include_router(workspaces.router, dependencies=[Depends(verify_token)])

