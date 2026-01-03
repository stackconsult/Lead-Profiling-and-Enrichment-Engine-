from __future__ import annotations

from typing import Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
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


app.include_router(jobs.router, dependencies=[Depends(verify_token)])
app.include_router(workspaces.router, dependencies=[Depends(verify_token)])

