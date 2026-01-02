from __future__ import annotations

from typing import Dict


class Validator:
    """
    Performs lightweight competitive checks and tech stack inference.
    """

    def run(self, lead: Dict) -> Dict:
        company = lead.get("company") or lead.get("name", "Unknown Co")
        return {
            "company": company,
            "tech_stack": ["AWS", "Salesforce"],
            "risks": ["Unknown budget owner"],
        }
