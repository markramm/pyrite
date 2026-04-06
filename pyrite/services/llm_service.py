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
        - ``"openai"`` — uses the ``openai`` SDK
        - ``"openrouter"`` — OpenRouter via OpenAI-compatible API
        - ``"ollama"`` — Ollama local models via OpenAI-compatible API
        - ``"gemini"`` — Google Gemini via OpenAI-compatible API
        - ``"stub"`` / ``"none"`` / ``""`` — no-op that returns empty strings / vectors
    """

    # Providers that use the OpenAI SDK under the hood
    _OPENAI_COMPAT_PROVIDERS = ("openai", "gemini", "openrouter", "ollama", "local")

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = settings.ai_provider or "stub"
        if self._provider in ("none", ""):
            self._provider = "stub"

    # -- public helpers -----------------------------------------------------

    @property
    def provider_name(self) -> str:
        return self._provider

    def _requires_api_key(self) -> bool:
        """Whether the current provider requires an API key."""
        return self._provider not in ("stub", "none", "", "ollama")

    def status(self) -> dict[str, Any]:
        """Return a JSON-safe status dict for the /api/ai/status endpoint."""
        if self._provider in ("stub", "none", ""):
            configured = False
        elif self._provider == "ollama":
            # Ollama doesn't require an API key — just needs provider + model
            configured = True
        else:
            configured = bool(self._settings.ai_api_key)
        return {
            "configured": configured,
            "provider": self._provider,
            "model": self._settings.ai_model,
        }

    # -- core API -----------------------------------------------------------

    def with_user_key(
        self,
        api_key: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> "LLMService":
        """Return a new LLMService instance with user-provided overrides.

        This creates a copy of the underlying Settings with the user's API key
        (and optionally provider/model) substituted in, so the original service
        remains unmodified.
        """
        settings = Settings(
            ai_provider=provider or self._settings.ai_provider,
            ai_api_key=api_key,
            ai_model=model or self._settings.ai_model,
            ai_api_base=self._settings.ai_api_base,
        )
        # Apply default base URL for Gemini when switching provider
        if settings.ai_provider == "gemini" and not settings.ai_api_base:
            settings.ai_api_base = "https://generativelanguage.googleapis.com/v1beta/openai/"
        return LLMService(settings)

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
        if self._provider in self._OPENAI_COMPAT_PROVIDERS:
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
        if self._provider in self._OPENAI_COMPAT_PROVIDERS:
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
        if self._provider in self._OPENAI_COMPAT_PROVIDERS:
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

    def _resolve_base_url(self) -> str | None:
        """Resolve the effective base URL for the current provider."""
        if self._settings.ai_api_base:
            return self._settings.ai_api_base
        # Default base URLs for providers that need them
        if self._provider == "ollama":
            return "http://localhost:11434/v1"
        return None

    def test_connection(self) -> dict[str, Any]:
        """Actually test the connection to the configured provider.

        Returns a dict with ``ok`` (bool) and ``message`` (str).
        For Ollama, validates the model exists on the server.
        """
        status = self.status()
        if not status["configured"]:
            return {"ok": False, "message": "AI provider is not configured"}

        try:
            if self._provider == "anthropic":
                # Send a minimal request to verify credentials
                client = self._get_anthropic_client()
                client.messages.create(
                    model=self._settings.ai_model,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}],
                )
                return {"ok": True, "message": f"Connected: {self._provider} ({self._settings.ai_model})"}

            if self._provider in self._OPENAI_COMPAT_PROVIDERS:
                client = self._get_openai_client()
                if self._provider == "ollama":
                    # Ollama supports model listing — verify the model exists
                    base = self._resolve_base_url() or "http://localhost:11434/v1"
                    # Strip /v1 to get the Ollama API root
                    ollama_root = base.rstrip("/")
                    if ollama_root.endswith("/v1"):
                        ollama_root = ollama_root[:-3]
                    import urllib.request
                    import json as _json

                    req = urllib.request.Request(f"{ollama_root}/api/tags", method="GET")
                    try:
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            data = _json.loads(resp.read())
                    except (urllib.error.URLError, OSError) as exc:
                        return {"ok": False, "message": f"Cannot reach Ollama at {ollama_root}: {exc}"}
                    available = [m["name"] for m in data.get("models", [])]
                    model = self._settings.ai_model
                    # Ollama model names can be "llama3.2" or "llama3.2:latest"
                    matched = any(
                        model == name or model == name.split(":")[0]
                        for name in available
                    )
                    if not matched:
                        short_list = ", ".join(available[:8])
                        suffix = f" (and {len(available) - 8} more)" if len(available) > 8 else ""
                        return {
                            "ok": False,
                            "message": f"Ollama is running but model '{model}' not found. Available: {short_list}{suffix}",
                        }
                    return {"ok": True, "message": f"Connected: Ollama ({model})"}
                else:
                    # For other OpenAI-compat providers, do a minimal completion
                    client.chat.completions.create(
                        model=self._settings.ai_model,
                        messages=[{"role": "user", "content": "hi"}],
                        max_tokens=1,
                    )
                    return {"ok": True, "message": f"Connected: {self._provider} ({self._settings.ai_model})"}

        except Exception as exc:
            msg = str(exc)
            # Truncate long error messages
            if len(msg) > 200:
                msg = msg[:200] + "..."
            return {"ok": False, "message": f"Connection failed: {msg}"}

        return {"ok": False, "message": f"Unknown provider: {self._provider}"}

    # -- OpenAI backend (also OpenRouter, Ollama) ---------------------------

    def _get_openai_client(self):
        mod = _import_openai()
        if mod is None:
            raise RuntimeError(
                "The 'openai' package is required for the OpenAI/OpenRouter/Ollama provider. "
                "Install it with: pip install 'pyrite[ai]'"
            )
        kwargs: dict[str, Any] = {"api_key": self._settings.ai_api_key or "no-key"}
        base_url = self._resolve_base_url()
        if base_url:
            kwargs["base_url"] = base_url
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
