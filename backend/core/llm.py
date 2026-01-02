"""
Unified LLM client wrapper for OpenAI and Gemini providers.

This module purposefully keeps the interface minimal so it can be extended
without breaking callers. It supports plugging in search/retrieval helpers
but does not hardcode external API keys; those are supplied per workspace.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol


class LLMBackend(Protocol):
    async def generate(self, prompt: str) -> Dict:
        ...


@dataclass
class LLMKeys:
    provider: str
    openai: Optional[str] = None
    tavily: Optional[str] = None
    gemini: Optional[str] = None


class StubLLMBackend:
    """
    Lightweight fallback used in tests or when keys are absent.
    """

    async def generate(self, prompt: str) -> Dict:
        return {"content": f"[stubbed] {prompt[:80]}", "citations": []}


class LLMClient:
    """
    Facade that selects an underlying backend based on provider string.

    Real implementations for OpenAI and Gemini can be slotted in later
    without changing the public interface.
    """

    def __init__(self, keys: LLMKeys):
        self.keys = keys
        self.backend: LLMBackend = StubLLMBackend()
        # Future: add concrete backends when API keys are present.

    async def generate(self, prompt: str) -> Dict:
        return await self.backend.generate(prompt)

    async def batch_generate(self, prompts: List[str]) -> List[Dict]:
        return [await self.generate(p) for p in prompts]
