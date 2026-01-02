# Lead Profiling and Enrichment Engine

Add leads, let the backend automation engine research, profile, and grade them so you understand them better than they understand themselves. Then start connecting and making sales.

## ProspectPulse – Lead Profiling & Enrichment (Streamlit + FastAPI + Valkey)

### Overview
- **Frontend:** Streamlit (`frontend/`) auto-deployable from GitHub.
- **Backend:** FastAPI (`backend/api`) with Server-Sent Events for live job updates.
- **Queue/Store:** Valkey (Redis-compatible) for job metadata, lead results, and workspace configs (not Streamlit state).
- **Worker:** RQ worker (`backend/worker.py`) for background processing.
- **Cost:** $0/month on Render free tiers + Streamlit Cloud free tier for MVP capacity (~500 leads/day).

### Architecture (Phase 1 MVP)
- Streamlit UI → calls FastAPI `/enqueue`, `/status/{job_id}`, `/leads`, `/stream/{job_id}`.
- FastAPI enqueues jobs to RQ (Valkey). In local/dev without Valkey, processing falls back inline.
- Agent pipeline: Miner → Validator → Synthesizer → stores results in `leads:{lead_id}` and updates `jobs:{job_id}` status.
- Valkey connection via `backend/core/valkey.py` (connection pool + in-memory fake for tests).

### File Map
- `backend/core/`: `valkey.py`, `llm.py` (stub dual LLM facade), `rate_limiter.py`.
- `backend/agents/`: `miner.py`, `validator.py`, `synthesizer.py`, `pipeline.py`.
- `backend/api/`: `main.py`, `jobs.py`, `workspaces.py`.
- `backend/worker.py`: RQ worker entrypoint.
- `frontend/`: Streamlit app, pages, components (SSE listener).
- `render.yaml`: Render IAC (web, worker, valkey).
- `.github/workflows/`: CI (pytest), Streamlit notify, keep-alive cron.

### Local Development
1) Install backend deps: `pip install -r backend/requirements.txt`
2) (Optional) start Valkey locally: `docker run -p 6379:6379 valkey/valkey:latest`
3) Run API: `uvicorn backend.api.main:app --reload --port 10000`
4) Run Streamlit: `cd frontend && streamlit run app.py` (ensure `API_URL` points to API)

Environment variables:
- `VALKEY_URL` (preferred) or `VALKEY_HOST`/`VALKEY_PORT`
- `API_URL` for Streamlit (defaults to `http://localhost:10000`)

### Tests
```bash
pip install -r backend/requirements.txt
pytest
```

### Deployment (Render + Streamlit Cloud)
- Push to GitHub.
- Render: create Web Service from `backend/` with `render.yaml`, plus Worker service and Valkey (auto-provisioned, free plan).
- Streamlit Cloud: point to `frontend/app.py`; Streamlit auto-redeploys on `main`.

### Notes & Guarantees
- Streamlit state stays in `st.session_state`; Valkey stores backend data only.
- RQ worker uses default queue; free tier on Render supports 1 web + 1 worker.
- SSE endpoint polls Valkey; can be upgraded to pub/sub later.
