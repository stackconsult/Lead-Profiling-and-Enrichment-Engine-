"""
Unified LLM client wrapper for OpenAI and Gemini providers.

This module purposefully keeps the interface minimal so it can be extended
without breaking callers. It supports plugging in search/retrieval helpers
but does not hardcode external API keys; those are supplied per workspace.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol


class LLMBackend(Protocol):
    def generate(self, prompt: str) -> Dict:
        ...


@dataclass
class LLMKeys:
    provider: str
    openai: Optional[str] = None
    tavily: Optional[str] = None
    gemini: Optional[str] = None


class StubLLMBackend:
    """
    Fallback used when keys are absent. Returns a deterministic message.
    """

    def generate(self, prompt: str) -> Dict:
        return {"content": "LLM keys missing; please add keys in Workspaces.", "citations": []}


class OpenAIBackend:
    def __init__(self, api_key: str):
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("openai package not installed") from exc
        self.client = OpenAI(api_key=api_key)

    def generate(self, prompt: str) -> Dict:
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.6,
        )
        content = completion.choices[0].message.content if completion.choices else ""
        return {"content": content or "", "citations": []}


class GeminiBackend:
    def __init__(self, api_key: str):
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("google-generativeai package not installed") from exc
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def generate(self, prompt: str) -> Dict:
        response = self.model.generate_content(prompt)
        content = getattr(response, "text", "") or ""
        return {"content": content, "citations": []}


class LLMClient:
    """
    Facade that selects an underlying backend based on provider string.
    """

    def __init__(self, keys: LLMKeys):
        self.keys = keys
        self.backend: LLMBackend = self._select_backend(keys)

    @staticmethod
    def _select_backend(keys: LLMKeys) -> LLMBackend:
        if keys.provider == "openai" and keys.openai:
            try:
                return OpenAIBackend(keys.openai)
            except Exception:
                return StubLLMBackend()
        if keys.provider == "gemini" and keys.gemini:
            try:
                return GeminiBackend(keys.gemini)
            except Exception:
                return StubLLMBackend()
        return StubLLMBackend()

    def generate(self, prompt: str) -> Dict:
        return self.backend.generate(prompt)

    def batch_generate(self, prompts: List[str]) -> List[Dict]:
        return [self.generate(p) for p in prompts]


# Global client instance using environment variables or defaults
llm_keys = LLMKeys(
    provider=os.getenv("LLM_PROVIDER", "openai"),
    openai=os.getenv("OPENAI_API_KEY"),
    gemini=os.getenv("GEMINI_API_KEY"),
    tavily=os.getenv("TAVILY_API_KEY"),
)

llm_client = LLMClient(llm_keys)
