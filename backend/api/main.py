from __future__ import annotations

from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/health")
async def health() -> Dict[str, str]:
    try:
        valkey_client.ping()
    except Exception as exc:
        return {"status": "degraded", "detail": str(exc)}
    return {"status": "ok"}


app.include_router(jobs.router)
app.include_router(workspaces.router)

