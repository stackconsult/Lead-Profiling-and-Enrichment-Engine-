from __future__ import annotations

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.core.config import config
from backend.api import jobs, workspaces, enterprise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with configuration validation"""
    # Startup validation
    try:
        config.validate_for_startup()
        print(f"✅ Configuration validated for {config.env} environment")
        print(f"✅ API running on {config.host}:{config.port}")
        print(f"✅ Valkey configured for {config.valkey_host}:{config.valkey_port}")
    except ValueError as e:
        print(f"❌ CRITICAL: Configuration validation failed: {e}")
        raise
    
    yield
    
    # Cleanup
    print("🔄 Application shutting down...")


app = FastAPI(
    title="ProspectPulse API",
    description="Lead profiling and enrichment engine",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
async def health_check():
    """Health check endpoint for Render (legacy path)"""
    try:
        # Test Valkey connection
        valkey_client.ping()
        return {"status": "healthy", "valkey": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.get("/health")
async def health_check_main():
    """Main health check endpoint"""
    try:
        # Test Valkey connection
        valkey_client.ping()
        return {"status": "healthy", "valkey": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")


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
                
                # Exit if job is complete
                if current_status == 'complete':
                    break
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'detail': str(e)})}\n\n"
                break
    
    return StreamingResponse(event_stream(), media_type="text/plain")


def verify_token(x_api_token: Optional[str] = Header(default=None)) -> None:
    import os

    expected = os.getenv("API_TOKEN")
    if expected and x_api_token != expected:
        raise HTTPException(status_code=401, detail="invalid API token")


app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(workspaces.router, prefix="/api", tags=["workspaces"])
app.include_router(enterprise.router, prefix="/api", tags=["enterprise"])
