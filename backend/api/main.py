from __future__ import annotations

import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.core.config import config
from backend.core.valkey import get_client
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
        client = get_client()
        client.ping()
        return {"status": "healthy", "valkey": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")


@app.get("/health")
async def health() -> Dict[str, str]:
    """Main health check endpoint"""
    try:
        client = get_client()
        client.ping()
        return {"status": "ok", "valkey": "connected"}
    except Exception as exc:
        return {"status": "degraded", "detail": str(exc)}


app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(workspaces.router, prefix="/api", tags=["workspaces"])
app.include_router(enterprise.router, tags=["enterprise"])
