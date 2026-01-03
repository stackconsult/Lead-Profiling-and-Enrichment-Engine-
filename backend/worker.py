from __future__ import annotations

import os
import json
from typing import Dict, Optional

from backend.agents.pipeline import AgentPipeline
from backend.core.valkey import set_job_status, valkey_client
from backend.core.llm import llm_client


def process_lead(lead: Dict, job_id: Optional[str] = None, workspace: Optional[Dict] = None) -> Dict:
    """
    Process a single lead through the agent pipeline.
    Can be called directly or via RQ worker.
    """
    try:
        if job_id:
            set_job_status(job_id, "processing", progress=0.1)
        
        pipeline = AgentPipeline(workspace=workspace)
        
        if job_id:
            set_job_status(job_id, "processing", progress=0.3)
        
        result = pipeline.run(lead, job_id=job_id)
        
        if job_id:
            set_job_status(job_id, "completed", progress=1.0)
            # Store result in Valkey for retrieval
            valkey_client.set(f"leads:{lead.get('id', 'unknown')}", json.dumps(result))
        
        return result
        
    except Exception as e:
        if job_id:
            set_job_status(job_id, "failed", error=str(e))
        raise


# RQ worker setup
def setup_rq_worker():
    """Initialize RQ worker with proper connection"""
    try:
        import rq
        from rq import Worker, Queue, Connection
        
        # Get Valkey connection
        conn = valkey_client
        
        # Listen to the default queue
        q = Queue(connection=conn)
        
        # Create worker
        worker = Worker([q], connection=conn)
        
        return worker
        
    except ImportError:
        print("RQ not installed. Install with: pip install rq")
        return None


def start_worker():
    """Start the RQ worker process"""
    worker = setup_rq_worker()
    if worker:
        worker.work()


if __name__ == "__main__":
    # Check if running as RQ worker or standalone
    if os.getenv("RUN_RQ_WORKER"):
        start_worker()
    else:
        # Allow running `python backend/worker.py` locally for inline processing tests.
        demo_lead = {"company": "Acme Corp", "id": "demo-lead"}
        result = process_lead(demo_lead, job_id="demo-job")
        print("Demo result:", json.dumps(result, indent=2))
