"""Tests for LLM Abstraction Service."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from pyrite.config import Settings

# ---------------------------------------------------------------------------
# Config round-trip tests
# ---------------------------------------------------------------------------


class TestSettingsAIFields:
    """Test that new AI settings fields work correctly."""

    def test_default_settings(self):
        s = Settings()
        assert s.ai_provider == "stub"
        assert s.ai_model == "claude-sonnet-4-20250514"
        assert s.ai_api_base == ""

    def test_custom_provider(self):
        s = Settings(ai_provider="anthropic", ai_model="claude-sonnet-4-20250514")
        assert s.ai_provider == "anthropic"
        assert s.ai_model == "claude-sonnet-4-20250514"

    def test_openrouter_provider(self):
        s = Settings(
            ai_provider="openai",
            ai_model="openai/gpt-4o",
            ai_api_base="https://openrouter.ai/api/v1",
        )
        assert s.ai_provider == "openai"
        assert s.ai_api_base == "https://openrouter.ai/api/v1"

    def test_ollama_provider(self):
        s = Settings(
            ai_provider="openai",
            ai_model="llama3",
            ai_api_base="http://localhost:11434/v1",
        )
        assert s.ai_api_base == "http://localhost:11434/v1"


# ---------------------------------------------------------------------------
# LLMService tests
# ---------------------------------------------------------------------------


class TestLLMServiceStub:
    """Test stub provider returns empty results."""

    def test_stub_complete(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="stub")
        svc = LLMService(settings)
        result = asyncio.run(svc.complete("Hello"))
        assert result == ""

    def test_stub_embed(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="stub")
        svc = LLMService(settings)
        result = asyncio.run(svc.embed(["hello", "world"]))
        assert result == [[], []]

    def test_stub_stream(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="stub")
        svc = LLMService(settings)

        async def collect():
            chunks = []
            async for chunk in svc.stream("Hello"):
                chunks.append(chunk)
            return chunks

        result = asyncio.run(collect())
        assert result == []

    def test_empty_provider_is_stub(self):
        """Empty or 'none' provider acts as stub."""
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="none")
        svc = LLMService(settings)
        result = asyncio.run(svc.complete("Hello"))
        assert result == ""

    def test_status(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="stub", ai_model="test-model")
        svc = LLMService(settings)
        status = svc.status()
        assert status["configured"] is False
        assert status["provider"] == "stub"
        assert status["model"] == "test-model"


class TestLLMServiceProviderSelection:
    """Test provider selection logic."""

    def test_anthropic_selected(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="anthropic", ai_model="claude-sonnet-4-20250514")
        svc = LLMService(settings)
        assert svc.provider_name == "anthropic"

    def test_openai_selected(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="openai", ai_model="gpt-4o")
        svc = LLMService(settings)
        assert svc.provider_name == "openai"

    def test_configured_status_for_real_providers(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="anthropic", ai_api_key="sk-test-key")
        svc = LLMService(settings)
        status = svc.status()
        assert status["configured"] is True


class TestLLMServiceMissingSDK:
    """Test that missing SDK raises helpful error."""

    def test_anthropic_missing_sdk_error(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="anthropic", ai_api_key="sk-test")
        svc = LLMService(settings)

        with patch.dict("sys.modules", {"anthropic": None}):
            with patch("pyrite.services.llm_service._import_anthropic", return_value=None):
                with pytest.raises(RuntimeError, match="anthropic"):
                    asyncio.run(svc.complete("Hello"))

    def test_openai_missing_sdk_error(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="openai", ai_api_key="sk-test")
        svc = LLMService(settings)

        with patch("pyrite.services.llm_service._import_openai", return_value=None):
            with pytest.raises(RuntimeError, match="openai"):
                asyncio.run(svc.complete("Hello"))


class TestLLMServiceAnthropicMocked:
    """Test Anthropic provider with mocked SDK."""

    def test_complete_calls_anthropic(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(
            ai_provider="anthropic", ai_api_key="sk-test", ai_model="claude-sonnet-4-20250514"
        )
        svc = LLMService(settings)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello back!")]
        mock_client.messages.create = MagicMock(return_value=mock_response)

        mock_module = MagicMock()
        mock_module.Anthropic.return_value = mock_client

        with patch("pyrite.services.llm_service._import_anthropic", return_value=mock_module):
            result = asyncio.run(svc.complete("Hello", system="Be helpful"))

        assert result == "Hello back!"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["system"] == "Be helpful"


class TestLLMServiceOpenAIMocked:
    """Test OpenAI provider with mocked SDK."""

    def test_complete_calls_openai(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="openai", ai_api_key="sk-test", ai_model="gpt-4o")
        svc = LLMService(settings)

        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "GPT says hi!"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)

        mock_module = MagicMock()
        mock_module.OpenAI.return_value = mock_client

        with patch("pyrite.services.llm_service._import_openai", return_value=mock_module):
            result = asyncio.run(svc.complete("Hello", system="Be helpful"))

        assert result == "GPT says hi!"
        mock_client.chat.completions.create.assert_called_once()

    def test_embed_calls_openai(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="openai", ai_api_key="sk-test", ai_model="gpt-4o")
        svc = LLMService(settings)

        mock_client = MagicMock()
        mock_data_0 = MagicMock()
        mock_data_0.embedding = [0.1, 0.2, 0.3]
        mock_data_1 = MagicMock()
        mock_data_1.embedding = [0.4, 0.5, 0.6]
        mock_response = MagicMock()
        mock_response.data = [mock_data_0, mock_data_1]
        mock_client.embeddings.create = MagicMock(return_value=mock_response)

        mock_module = MagicMock()
        mock_module.OpenAI.return_value = mock_client

        with patch("pyrite.services.llm_service._import_openai", return_value=mock_module):
            result = asyncio.run(svc.embed(["hello", "world"]))

        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    def test_openai_with_custom_base_url(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(
            ai_provider="openai",
            ai_api_key="sk-test",
            ai_model="llama3",
            ai_api_base="http://localhost:11434/v1",
        )
        svc = LLMService(settings)

        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Ollama says hi!"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)

        mock_module = MagicMock()
        mock_module.OpenAI.return_value = mock_client

        with patch("pyrite.services.llm_service._import_openai", return_value=mock_module):
            result = asyncio.run(svc.complete("Hello"))

        assert result == "Ollama says hi!"
        # Verify base_url was passed to OpenAI constructor
        mock_module.OpenAI.assert_called_once()
        call_kwargs = mock_module.OpenAI.call_args[1]
        assert call_kwargs["base_url"] == "http://localhost:11434/v1"


# ---------------------------------------------------------------------------
# API endpoint test
# ---------------------------------------------------------------------------


class TestAIStatusEndpoint:
    """Test /api/ai/status endpoint."""

    def test_ai_status_returns_config(self):
        from fastapi.testclient import TestClient

        from pyrite.server.api import app

        with TestClient(app) as client:
            # Reset the cached config to force fresh load
            import pyrite.server.api as api_module

            old_config = api_module._config
            api_module._config = None

            try:
                response = client.get("/api/ai/status")
                assert response.status_code == 200
                data = response.json()
                assert "configured" in data
                assert "provider" in data
                assert "model" in data
                assert isinstance(data["configured"], bool)
                assert isinstance(data["provider"], str)
                assert isinstance(data["model"], str)
            finally:
                api_module._config = old_config
