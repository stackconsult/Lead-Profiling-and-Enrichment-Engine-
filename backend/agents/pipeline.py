from __future__ import annotations

import uuid
from typing import Dict

from backend.agents.miner import Miner
from backend.agents.synthesizer import Synthesizer
from backend.agents.validator import Validator
from backend.core.valkey import set_job_status, valkey_client


class AgentPipeline:
    """
    Orchestrates the miner, validator, and synthesizer steps.
    """

    def __init__(self, workspace_id: str | None = None):
        self.workspace_id = workspace_id
        self.miner = Miner()
        self.validator = Validator()
        self.synthesizer = Synthesizer()

    def run(self, lead: Dict, job_id: str | None = None) -> Dict:
        job_key = f"jobs:{job_id}" if job_id else None
        try:
            if job_key:
                set_job_status(job_id, "mining", progress=0.2)
            mined = self.miner.run(lead)

            if job_key:
                set_job_status(job_id, "validating", progress=0.5)
            validated = self.validator.run(lead)

            synthesized = self.synthesizer.run(lead, mined, validated)
            lead_id = lead.get("id") or str(uuid.uuid4())
            valkey_client.hset(f"leads:{lead_id}", mapping=synthesized)
            if job_key:
                valkey_client.lpush(f"{job_key}:leads", lead_id)
                set_job_status(job_id, "complete", progress=1.0)
            return {"id": lead_id, **synthesized}
        except Exception as exc:  # pragma: no cover - narrow for logging
            if job_key:
                set_job_status(job_id, "failed", error=str(exc))
            raise
