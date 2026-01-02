from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core import valkey


def setup_function():
    if hasattr(valkey.valkey_client, "flushdb"):
        valkey.valkey_client.flushdb()


def test_enqueue_and_status_and_leads():
    client = TestClient(app)
    leads = [{"company": "Acme Corp"}, {"company": "Beta LLC"}]
    resp = client.post("/enqueue", json=leads)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    status = client.get(f"/status/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "complete"

    leads_resp = client.get("/leads")
    assert leads_resp.status_code == 200
    items = leads_resp.json()["items"]
    assert len(items) == 2
