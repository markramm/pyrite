"""
Provider-agnostic LLM Abstraction Service.

Supports Anthropic (Claude), OpenAI (GPT), OpenRouter (200+ models),
Ollama (local), and a stub/no-op provider. SDKs are optional dependencies
imported only when needed.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from ..config import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy SDK imports — return the module or None
# ---------------------------------------------------------------------------


def _import_anthropic():
    """Try to import the anthropic SDK. Returns module or None."""
    try:
        import anthropic

        return anthropic
    except ImportError:
        return None


def _import_openai():
    """Try to import the openai SDK. Returns module or None."""
    try:
        import openai

        return openai
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# LLMService
# ---------------------------------------------------------------------------


class LLMService:
    """Provider-agnostic LLM interface.

    Providers:
        - ``"anthropic"`` — uses the ``anthropic`` SDK directly
        - ``"openai"`` — uses the ``openai`` SDK (also works for OpenRouter / Ollama
          via ``ai_api_base``)
        - ``"stub"`` / ``"none"`` / ``""`` — no-op that returns empty strings / vectors
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = settings.ai_provider or "stub"
        if self._provider in ("none", ""):
            self._provider = "stub"

    # -- public helpers -----------------------------------------------------

    @property
    def provider_name(self) -> str:
        return self._provider

    def status(self) -> dict[str, Any]:
        """Return a JSON-safe status dict for the /api/ai/status endpoint."""
        configured = self._provider not in ("stub", "none", "") and bool(self._settings.ai_api_key)
        return {
            "configured": configured,
            "provider": self._provider,
            "model": self._settings.ai_model,
        }

    # -- core API -----------------------------------------------------------

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Generate a completion and return the full text."""
        if self._provider == "stub":
            return ""
        if self._provider == "anthropic":
            return self._anthropic_complete(prompt, system, max_tokens)
        if self._provider in ("openai", "local"):
            return self._openai_complete(prompt, system, max_tokens)
        return ""

    async def stream(
        self,
        prompt: str,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion tokens as an async iterator."""
        if self._provider == "stub":
            return
        if self._provider == "anthropic":
            for chunk in self._anthropic_stream(prompt, system):
                yield chunk
            return
        if self._provider in ("openai", "local"):
            for chunk in self._openai_stream(prompt, system):
                yield chunk
            return

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Produce embedding vectors for the given texts."""
        if self._provider == "stub":
            return [[] for _ in texts]
        if self._provider == "anthropic":
            # Anthropic does not have an embeddings API — fall back to empty
            return [[] for _ in texts]
        if self._provider in ("openai", "local"):
            return self._openai_embed(texts)
        return [[] for _ in texts]

    # -- Anthropic backend --------------------------------------------------

    def _get_anthropic_client(self):
        mod = _import_anthropic()
        if mod is None:
            raise RuntimeError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install it with: pip install 'pyrite[ai]'"
            )
        kwargs: dict[str, Any] = {"api_key": self._settings.ai_api_key}
        if self._settings.ai_api_base:
            kwargs["base_url"] = self._settings.ai_api_base
        return mod.Anthropic(**kwargs)

    def _anthropic_complete(self, prompt: str, system: str | None, max_tokens: int) -> str:
        client = self._get_anthropic_client()
        kwargs: dict[str, Any] = {
            "model": self._settings.ai_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text

    def _anthropic_stream(self, prompt: str, system: str | None):
        client = self._get_anthropic_client()
        kwargs: dict[str, Any] = {
            "model": self._settings.ai_model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        if system:
            kwargs["system"] = system
        with client.messages.stream(**kwargs) as stream:
            yield from stream.text_stream

    # -- OpenAI backend (also OpenRouter, Ollama) ---------------------------

    def _get_openai_client(self):
        mod = _import_openai()
        if mod is None:
            raise RuntimeError(
                "The 'openai' package is required for the OpenAI/OpenRouter/Ollama provider. "
                "Install it with: pip install 'pyrite[ai]'"
            )
        kwargs: dict[str, Any] = {"api_key": self._settings.ai_api_key or "no-key"}
        if self._settings.ai_api_base:
            kwargs["base_url"] = self._settings.ai_api_base
        return mod.OpenAI(**kwargs)

    def _openai_complete(self, prompt: str, system: str | None, max_tokens: int) -> str:
        client = self._get_openai_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=self._settings.ai_model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def _openai_stream(self, prompt: str, system: str | None):
        client = self._get_openai_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=self._settings.ai_model,
            messages=messages,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _openai_embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_openai_client()
        response = client.embeddings.create(
            model=self._settings.embedding_model or "text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]
