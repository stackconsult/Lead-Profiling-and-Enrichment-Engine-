from __future__ import annotations

from backend.agents.pipeline import AgentPipeline
from backend.core.valkey import get_client


def decode_map(data):
    def _decode(v):
        return v.decode() if isinstance(v, (bytes, bytearray)) else v

    return {str(_decode(k)): _decode(v) for k, v in data.items()}


def setup_function():
    client = get_client()
    if hasattr(client, "flushdb"):
        client.flushdb()


def test_pipeline_runs_and_stores_lead():
    pipeline = AgentPipeline()
    lead = {"company": "Acme Corp"}
    result = pipeline.run(lead, job_id="job-1")

    assert result["company"] == "Acme Corp"
    
    client = get_client()
    stored = decode_map(client.hgetall(f"leads:{result['id']}"))
    assert stored["company"] == "Acme Corp"
    job = decode_map(client.hgetall("jobs:job-1"))
    assert job["status"] == "complete"
