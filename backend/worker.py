from __future__ import annotations

from typing import Dict, Optional

from backend.agents.pipeline import AgentPipeline
from backend.core.valkey import set_job_status


def process_lead(lead: Dict, job_id: Optional[str] = None, workspace: Optional[Dict] = None) -> Dict:
    pipeline = AgentPipeline(workspace=workspace)
    result = pipeline.run(lead, job_id=job_id)
    if job_id:
        set_job_status(job_id, "complete", progress=1.0)
    return result


if __name__ == "__main__":
    # Allow running `python backend/worker.py` locally for inline processing tests.
    demo_lead = {"company": "Acme Corp"}
    print(process_lead(demo_lead))
