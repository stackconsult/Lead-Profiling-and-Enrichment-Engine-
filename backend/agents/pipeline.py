from __future__ import annotations

import uuid
from typing import Dict, Optional

from backend.agents.miner import Miner
from backend.agents.synthesizer import Synthesizer
from backend.agents.validator import Validator
from backend.core.llm import LLMClient, LLMKeys
from backend.core.valkey import set_job_status, valkey_client


class AgentPipeline:
    """
    Orchestrates the miner, validator, and synthesizer steps.
    Refactored to eliminate simulation code and improve reliability.
    """

    def __init__(self, workspace: Optional[Dict] = None):
        self.workspace = workspace or {}
        self.workspace_id = self.workspace.get("id")
        
        # Initialize LLM client with workspace-specific keys
        provider = self.workspace.get("provider") or "openai"
        keys = LLMKeys(
            provider=provider,
            openai=self.workspace.get("openai_key"),
            gemini=self.workspace.get("gemini_key"),
            tavily=self.workspace.get("tavily_key"),
        )
        self.llm = LLMClient(keys)
        
        # Initialize agents with the LLM client
        self.miner = Miner(self.llm)
        self.validator = Validator(self.llm)
        self.synthesizer = Synthesizer(self.llm)

    def run(self, lead: Dict, job_id: str | None = None) -> Dict:
        """Run the pipeline with improved error handling and resource management"""
        job_key = f"jobs:{job_id}" if job_id else None
        
        try:
            if job_id:
                set_job_status(job_id, "mining", progress=0.1)
            
            # Step 1: Mine signals
            mined = self.miner.run(lead)
            
            if job_id:
                set_job_status(job_id, "validating", progress=0.4)
            
            # Step 2: Validate and analyze
            # Pass the mined signals to the validator
            lead_with_signals = {**lead, **mined}
            validated = self.validator.run(lead_with_signals)
            
            if job_id:
                set_job_status(job_id, "synthesizing", progress=0.7)
            
            # Step 3: Synthesize insights
            synthesized = self.synthesizer.run(lead, mined, validated)
            
            # Store results
            lead_id = lead.get("id") or str(uuid.uuid4())
            
            # Store synthesized results in Valkey
            result_data = {
                "id": lead_id,
                "company": lead.get("company", "Unknown"),
                "created_at": str(uuid.uuid4()),  # Simple timestamp
                **synthesized
            }
            
            valkey_client.hset(f"leads:{lead_id}", mapping=result_data)
            
            if job_id:
                valkey_client.lpush(f"{job_key}:leads", lead_id)
                set_job_status(job_id, "completed", progress=1.0)
            
            return {"id": lead_id, **synthesized}
            
        except Exception as exc:
            if job_id:
                set_job_status(job_id, "failed", error=str(exc))
            # Re-raise with context
            raise Exception(f"Pipeline failed for lead {lead.get('id', 'unknown')}: {exc}") from exc
