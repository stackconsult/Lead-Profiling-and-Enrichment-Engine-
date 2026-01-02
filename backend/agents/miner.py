from __future__ import annotations

from typing import Dict


class Miner:
    """
    Placeholder miner that would normally gather external signals
    (e.g., Reddit, G2, LinkedIn). For now returns synthetic findings.
    """

    def run(self, lead: Dict) -> Dict:
        company = lead.get("company") or lead.get("name", "Unknown Co")
        return {
            "company": company,
            "signals": [
                f"{company} mentioned cost pressures on forums",
                f"{company} evaluating cloud spend reduction",
            ],
        }
