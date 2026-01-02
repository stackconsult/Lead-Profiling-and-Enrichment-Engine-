from __future__ import annotations

from typing import Dict, List


class Synthesizer:
    """
    Combines mined signals and validation into a fit score and wedge.
    """

    def run(self, lead: Dict, mined: Dict, validated: Dict) -> Dict:
        company = lead.get("company") or lead.get("name", "Unknown Co")
        signals: List[str] = mined.get("signals", [])
        risk_penalty = len(validated.get("risks", [])) * 5
        base_score = 90 if signals else 70
        score = max(0, min(100, base_score - risk_penalty))

        wedge = f"{company} can trim tooling costs with your bundled pricing."
        if "cost" in " ".join(signals).lower():
            wedge = f"{company} faces cost pressure; lead with ROI and consolidation."

        return {
            "company": company,
            "fit_score": score,
            "wedge": wedge,
            "tech_stack": validated.get("tech_stack", []),
            "signals": signals,
        }
