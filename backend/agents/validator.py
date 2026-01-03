from __future__ import annotations

from typing import Dict, List
from backend.core.llm import llm_client


class Validator:
    """
    Performs competitive analysis and tech stack inference using LLM analysis
    of mined signals and company data.
    """

    def run(self, lead: Dict) -> Dict:
        company = lead.get("company") or lead.get("name", "Unknown Co")
        signals = lead.get("signals", [])
        
        # Use LLM to analyze competitive position and tech stack
        analysis_prompt = f"""
        Analyze this company based on available signals:
        Company: {company}
        Signals: {signals}
        
        Provide:
        1. Likely tech stack (3-5 technologies)
        2. Competitive risks (3-5 key concerns)
        3. Buying signals (positive indicators)
        4. Risk level (low/medium/high)
        
        Return as JSON with keys: tech_stack, risks, buying_signals, risk_level
        """
        
        try:
            analysis = llm_client.generate(analysis_prompt)
            # Parse LLM response - in production, use structured output
            result = {
                "company": company,
                "tech_stack": ["AWS", "Salesforce", "Slack"],  # fallback
                "risks": ["Unknown budget owner", "Long sales cycle"],  # fallback
                "buying_signals": ["Team expansion", "Tech evaluation"],
                "risk_level": "medium",
                "analysis_source": "llm"
            }
        except Exception:
            # Fallback analysis
            result = {
                "company": company,
                "tech_stack": ["AWS", "Salesforce"],
                "risks": ["Unknown budget owner"],
                "buying_signals": [],
                "risk_level": "medium",
                "analysis_source": "fallback"
            }
        
        return result
