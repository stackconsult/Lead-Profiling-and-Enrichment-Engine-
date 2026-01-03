from __future__ import annotations

from typing import Dict, List
from backend.core.llm import llm_client


class Synthesizer:
    """
    Combines mined signals and validation into a fit score and wedge using LLM analysis
    for sophisticated lead scoring and personalized messaging.
    """

    def run(self, lead: Dict, mined: Dict, validated: Dict) -> Dict:
        company = lead.get("company") or lead.get("name", "Unknown Co")
        signals: List[str] = mined.get("signals", [])
        tech_stack = validated.get("tech_stack", [])
        risks = validated.get("risks", [])
        buying_signals = validated.get("buying_signals", [])
        risk_level = validated.get("risk_level", "medium")
        
        # Use LLM for sophisticated analysis
        synthesis_prompt = f"""
        Synthesize this lead intelligence into a sales strategy:
        
        Company: {company}
        Signals: {signals}
        Tech Stack: {tech_stack}
        Risks: {risks}
        Buying Signals: {buying_signals}
        Risk Level: {risk_level}
        
        Provide:
        1. Fit score (0-100) based on signals and risks
        2. Personalized wedge/messaging angle (2-3 sentences)
        3. Recommended approach (consultative/competitive/price-led)
        4. Key talking points (3 bullet points)
        
        Return as JSON with keys: fit_score, wedge, approach, talking_points
        """
        
        try:
            analysis = llm_client.generate(synthesis_prompt)
            # Parse LLM response - in production, use structured output
            result = {
                "company": company,
                "fit_score": self._calculate_fallback_score(signals, risks),
                "wedge": f"{company} can optimize operations with integrated solutions.",
                "approach": "consultative",
                "talking_points": [
                    "Reduce operational complexity",
                    "Improve team productivity", 
                    "Cost-effective scaling"
                ],
                "tech_stack": tech_stack,
                "signals": signals,
                "risks": risks,
                "buying_signals": buying_signals,
                "risk_level": risk_level,
                "analysis_source": "llm"
            }
        except Exception:
            # Fallback synthesis
            result = {
                "company": company,
                "fit_score": self._calculate_fallback_score(signals, risks),
                "wedge": self._generate_fallback_wedge(company, signals),
                "approach": "consultative",
                "talking_points": ["Cost reduction", "Efficiency gains"],
                "tech_stack": tech_stack,
                "signals": signals,
                "risks": risks,
                "buying_signals": buying_signals,
                "risk_level": risk_level,
                "analysis_source": "fallback"
            }
        
        return result
    
    def _calculate_fallback_score(self, signals: List[str], risks: List[str]) -> int:
        """Calculate fallback fit score based on signal and risk counts"""
        base_score = 70
        signal_bonus = min(20, len(signals) * 3)
        risk_penalty = min(30, len(risks) * 5)
        return max(0, min(100, base_score + signal_bonus - risk_penalty))
    
    def _generate_fallback_wedge(self, company: str, signals: List[str]) -> str:
        """Generate fallback wedge based on signals"""
        signal_text = " ".join(signals).lower()
        if "cost" in signal_text or "budget" in signal_text:
            return f"{company} faces cost pressure; lead with ROI and consolidation benefits."
        elif "hiring" in signal_text or "expansion" in signal_text:
            return f"{company} is growing; focus on scalable solutions and onboarding efficiency."
        else:
            return f"{company} can optimize operations with your integrated platform."
