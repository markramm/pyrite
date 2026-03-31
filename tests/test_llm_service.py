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
            ai_provider="ollama",
            ai_model="llama3",
        )
        assert s.ai_provider == "ollama"

    def test_openrouter_native_provider(self):
        s = Settings(
            ai_provider="openrouter",
            ai_model="anthropic/claude-sonnet-4",
            ai_api_key="sk-or-test",
        )
        assert s.ai_provider == "openrouter"


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


class TestLLMServiceGemini:
    """Test Gemini provider routes through OpenAI backend."""

    def test_gemini_selected(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="gemini", ai_model="gemini-2.0-flash")
        svc = LLMService(settings)
        assert svc.provider_name == "gemini"

    def test_gemini_configured_status(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="gemini", ai_api_key="test-key")
        svc = LLMService(settings)
        status = svc.status()
        assert status["configured"] is True
        assert status["provider"] == "gemini"

    def test_gemini_complete_uses_openai_backend(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(
            ai_provider="gemini",
            ai_api_key="test-key",
            ai_model="gemini-2.0-flash",
            ai_api_base="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        svc = LLMService(settings)

        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Gemini says hi!"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = MagicMock(return_value=mock_response)

        mock_module = MagicMock()
        mock_module.OpenAI.return_value = mock_client

        with patch("pyrite.services.llm_service._import_openai", return_value=mock_module):
            result = asyncio.run(svc.complete("Hello"))

        assert result == "Gemini says hi!"
        mock_module.OpenAI.assert_called_once()
        call_kwargs = mock_module.OpenAI.call_args[1]
        assert "generativelanguage.googleapis.com" in call_kwargs["base_url"]

    def test_gemini_default_base_url_from_config(self):
        """Settings.__post_init__ sets Gemini base URL when not provided."""
        s = Settings(ai_provider="gemini", ai_api_key="test-key")
        assert "generativelanguage.googleapis.com" in s.ai_api_base

    def test_gemini_settings_valid(self):
        s = Settings(ai_provider="gemini", ai_model="gemini-2.0-flash")
        assert s.ai_provider == "gemini"
        assert s.ai_model == "gemini-2.0-flash"


class TestLLMServiceOllama:
    """Test Ollama provider routes through OpenAI backend."""

    def test_ollama_selected(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="ollama", ai_model="llama3.2")
        svc = LLMService(settings)
        assert svc.provider_name == "ollama"

    def test_ollama_configured_without_api_key(self):
        """Ollama should be configured even without an API key."""
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="ollama", ai_model="llama3.2")
        svc = LLMService(settings)
        status = svc.status()
        assert status["configured"] is True
        assert status["provider"] == "ollama"

    def test_ollama_does_not_require_api_key(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="ollama", ai_model="llama3.2")
        svc = LLMService(settings)
        assert svc._requires_api_key() is False

    def test_ollama_complete_uses_openai_backend(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="ollama", ai_model="llama3.2")
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
        mock_module.OpenAI.assert_called_once()
        call_kwargs = mock_module.OpenAI.call_args[1]
        assert call_kwargs["base_url"] == "http://localhost:11434/v1"

    def test_ollama_default_base_url(self):
        """Ollama should auto-resolve to localhost:11434/v1."""
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="ollama", ai_model="llama3.2")
        svc = LLMService(settings)
        assert svc._resolve_base_url() == "http://localhost:11434/v1"

    def test_ollama_custom_base_url(self):
        """User can override the Ollama base URL."""
        from pyrite.services.llm_service import LLMService

        settings = Settings(
            ai_provider="ollama",
            ai_model="llama3.2",
            ai_api_base="http://my-server:11434/v1",
        )
        svc = LLMService(settings)
        assert svc._resolve_base_url() == "http://my-server:11434/v1"


class TestLLMServiceOpenRouter:
    """Test OpenRouter as a first-class provider."""

    def test_openrouter_selected(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(
            ai_provider="openrouter",
            ai_api_key="sk-or-test",
            ai_model="anthropic/claude-sonnet-4",
        )
        svc = LLMService(settings)
        assert svc.provider_name == "openrouter"

    def test_openrouter_configured_with_key(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="openrouter", ai_api_key="sk-or-test")
        svc = LLMService(settings)
        status = svc.status()
        assert status["configured"] is True

    def test_openrouter_not_configured_without_key(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="openrouter")
        svc = LLMService(settings)
        status = svc.status()
        assert status["configured"] is False


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


class TestLLMServiceTestConnection:
    """Test the test_connection method."""

    def test_stub_not_configured(self):
        from pyrite.services.llm_service import LLMService

        settings = Settings(ai_provider="stub")
        svc = LLMService(settings)
        result = svc.test_connection()
        assert result["ok"] is False
        assert "not configured" in result["message"].lower()

    def test_ollama_unreachable(self):
        """When Ollama server is not running, test_connection should fail gracefully."""
        from pyrite.services.llm_service import LLMService

        settings = Settings(
            ai_provider="ollama",
            ai_model="llama3.2",
            ai_api_base="http://localhost:99999/v1",  # unlikely to be running
        )
        svc = LLMService(settings)
        result = svc.test_connection()
        assert result["ok"] is False
        assert "Cannot reach Ollama" in result["message"] or "Connection failed" in result["message"]

    def test_openai_bad_key(self):
        """OpenAI with invalid key should fail."""
        from pyrite.services.llm_service import LLMService

        settings = Settings(
            ai_provider="openai",
            ai_api_key="sk-fake",
            ai_model="gpt-4o",
        )
        svc = LLMService(settings)

        mock_module = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Invalid API key")
        mock_module.OpenAI.return_value = mock_client

        with patch("pyrite.services.llm_service._import_openai", return_value=mock_module):
            result = svc.test_connection()
        assert result["ok"] is False
        assert "Invalid API key" in result["message"]


class TestAIStatusEndpoint:
    """Test /api/ai/status endpoint."""

    def test_ai_status_returns_config(self):
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        app = create_app()
        with TestClient(app) as client:
            response = client.get("/api/ai/status")
            assert response.status_code == 200
            data = response.json()
            assert "configured" in data
            assert "provider" in data
            assert "model" in data
            assert isinstance(data["configured"], bool)
            assert isinstance(data["provider"], str)
            assert isinstance(data["model"], str)

    def test_ai_test_endpoint_exists(self):
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        app = create_app()
        with TestClient(app) as client:
            response = client.post("/api/ai/test")
            assert response.status_code == 200
            data = response.json()
            assert "ok" in data
            assert "message" in data
