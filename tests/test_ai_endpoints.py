"""Tests for AI endpoints: summarize, auto-tag, suggest-links, chat.

All tests use a mock LLM service — no real API calls.
Uses shared fixtures from conftest.py.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

import pyrite.server.api as api_module
from pyrite.server.api import create_app


class MockLLMService:
    """Mock LLM service for testing AI endpoints."""

    def __init__(self, configured=True, complete_response="Mock response", stream_tokens=None):
        self._configured = configured
        self._complete_response = complete_response
        self._stream_tokens = stream_tokens or ["Hello", " world"]

    def status(self):
        return {
            "configured": self._configured,
            "provider": "mock",
            "model": "test-model",
        }

    async def complete(self, prompt, system=None, max_tokens=1024):
        return self._complete_response

    async def stream(self, prompt, system=None):
        for token in self._stream_tokens:
            yield token


@pytest.fixture
def ai_env(indexed_test_env):
    """Test environment for AI endpoint tests with mock LLM."""
    config = indexed_test_env["config"]
    db = indexed_test_env["db"]
    index_mgr = indexed_test_env["index_mgr"]

    api_module._config = config
    api_module._db = db
    api_module._index_mgr = index_mgr
    api_module._kb_service = None

    app = create_app(config)
    client = TestClient(app)

    yield {
        "client": client,
        "app": app,
        "config": config,
        "db": db,
    }

    api_module._config = None
    api_module._db = None
    api_module._index_mgr = None
    api_module._kb_service = None


def _inject_llm(app, llm):
    """Override LLM service dependency."""
    from pyrite.server.api import get_llm_service

    app.dependency_overrides[get_llm_service] = lambda: llm


@pytest.mark.api
class TestAISummarize:
    def test_summarize_returns_summary(self, ai_env):
        llm = MockLLMService(complete_response="This is a summary of the event.")
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/summarize",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "This is a summary of the event."

    def test_summarize_empty_body(self, ai_env):
        """Entry with empty body returns special message."""
        # Create entry with empty body
        from pyrite.services.kb_service import KBService

        svc = KBService(ai_env["config"], ai_env["db"])
        svc.create_entry("test-events", "empty-entry", "Empty Entry", "note", body="")

        llm = MockLLMService()
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/summarize",
            json={"entry_id": "empty-entry", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        assert resp.json()["summary"] == "(No content to summarize)"

    def test_summarize_entry_not_found(self, ai_env):
        llm = MockLLMService()
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/summarize",
            json={"entry_id": "nonexistent", "kb_name": "test-events"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_FOUND"

    def test_summarize_ai_not_configured(self, ai_env):
        llm = MockLLMService(configured=False)
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/summarize",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "AI_NOT_CONFIGURED"

    def test_summarize_llm_error(self, ai_env):
        """LLM exception returns 500 with AI_ERROR code."""
        llm = MockLLMService()
        llm.complete = AsyncMock(side_effect=RuntimeError("Provider timeout"))
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/summarize",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 500
        assert resp.json()["detail"]["code"] == "AI_ERROR"


@pytest.mark.api
class TestAIAutoTag:
    def test_auto_tag_returns_suggestions(self, ai_env):
        tags_json = json.dumps([
            {"name": "policy", "is_new": False, "reason": "Content about policy"},
            {"name": "executive-order", "is_new": True, "reason": "Mentions executive orders"},
        ])
        llm = MockLLMService(complete_response=tags_json)
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/auto-tag",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggested_tags"]) == 2
        assert data["suggested_tags"][0]["name"] == "policy"
        assert data["suggested_tags"][1]["is_new"] is True

    def test_auto_tag_strips_markdown_code_blocks(self, ai_env):
        """JSON wrapped in ```json ... ``` is parsed correctly."""
        wrapped = '```json\n[{"name": "test", "is_new": false, "reason": "r"}]\n```'
        llm = MockLLMService(complete_response=wrapped)
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/auto-tag",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["suggested_tags"]) == 1

    def test_auto_tag_non_json_returns_empty(self, ai_env):
        """Non-JSON LLM response returns empty suggestions."""
        llm = MockLLMService(complete_response="I can't generate tags right now.")
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/auto-tag",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        assert resp.json()["suggested_tags"] == []

    def test_auto_tag_entry_not_found(self, ai_env):
        llm = MockLLMService()
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/auto-tag",
            json={"entry_id": "nonexistent", "kb_name": "test-events"},
        )
        assert resp.status_code == 404


@pytest.mark.api
class TestAISuggestLinks:
    def test_suggest_links_returns_suggestions(self, ai_env):
        """When search finds related entries, LLM suggestions are returned."""
        from pyrite.server.api import get_search_service

        links_json = json.dumps([
            {"target_id": "2025-01-11--test-event-1", "target_title": "Test Event 1", "reason": "Related event"},
        ])
        llm = MockLLMService(complete_response=links_json)
        _inject_llm(ai_env["app"], llm)

        mock_svc = MagicMock()
        mock_svc.search.return_value = [
            {"id": "2025-01-11--test-event-1", "title": "Test Event 1", "entry_type": "event", "snippet": "immigration"},
            {"id": "2025-01-12--test-event-2", "title": "Test Event 2", "entry_type": "event", "snippet": "immigration"},
        ]
        ai_env["app"].dependency_overrides[get_search_service] = lambda: mock_svc

        resp = ai_env["client"].post(
            "/api/ai/suggest-links",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["target_id"] == "2025-01-11--test-event-1"
        assert data["suggestions"][0]["target_kb"] == "test-events"

    def test_suggest_links_no_related_returns_empty(self, ai_env):
        """When search finds no related entries, returns empty suggestions."""
        from pyrite.server.api import get_search_service

        llm = MockLLMService()
        _inject_llm(ai_env["app"], llm)

        mock_svc = MagicMock()
        mock_svc.search.return_value = []
        ai_env["app"].dependency_overrides[get_search_service] = lambda: mock_svc

        resp = ai_env["client"].post(
            "/api/ai/suggest-links",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        assert resp.json()["suggestions"] == []

    def test_suggest_links_non_json_returns_empty(self, ai_env):
        from pyrite.server.api import get_search_service

        llm = MockLLMService(complete_response="Not valid JSON")
        _inject_llm(ai_env["app"], llm)

        mock_svc = MagicMock()
        mock_svc.search.return_value = [
            {"id": "2025-01-11--test-event-1", "title": "Test Event 1", "entry_type": "event", "snippet": "x"},
        ]
        ai_env["app"].dependency_overrides[get_search_service] = lambda: mock_svc

        resp = ai_env["client"].post(
            "/api/ai/suggest-links",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        assert resp.json()["suggestions"] == []

    def test_suggest_links_filters_invalid_items(self, ai_env):
        """Items without target_id are filtered out."""
        from pyrite.server.api import get_search_service

        links_json = json.dumps([
            {"target_id": "2025-01-11--test-event-1", "target_title": "Valid", "reason": "ok"},
            {"no_id": True},
            "not a dict",
        ])
        llm = MockLLMService(complete_response=links_json)
        _inject_llm(ai_env["app"], llm)

        mock_svc = MagicMock()
        mock_svc.search.return_value = [
            {"id": "2025-01-11--test-event-1", "title": "Test Event 1", "entry_type": "event", "snippet": "x"},
        ]
        ai_env["app"].dependency_overrides[get_search_service] = lambda: mock_svc

        resp = ai_env["client"].post(
            "/api/ai/suggest-links",
            json={"entry_id": "2025-01-10--test-event-0", "kb_name": "test-events"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["suggestions"]) == 1

    def test_suggest_links_entry_not_found(self, ai_env):
        llm = MockLLMService()
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/suggest-links",
            json={"entry_id": "nonexistent", "kb_name": "test-events"},
        )
        assert resp.status_code == 404


@pytest.mark.api
class TestAIChat:
    def test_chat_streams_tokens(self, ai_env):
        llm = MockLLMService(stream_tokens=["Token1", " Token2"])
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/chat",
            json={
                "messages": [{"role": "user", "content": "Tell me about immigration"}],
                "kb": "test-events",
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        # Parse SSE events
        events = []
        for line in resp.text.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        # Should have token events + sources + done
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "Token1"
        assert token_events[1]["content"] == " Token2"

        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1

    def test_chat_includes_sources(self, ai_env):
        llm = MockLLMService(stream_tokens=["Answer"])
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/chat",
            json={
                "messages": [{"role": "user", "content": "immigration policy"}],
                "kb": "test-events",
            },
        )
        events = []
        for line in resp.text.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        source_events = [e for e in events if e["type"] == "sources"]
        # Should have sources since we indexed events about immigration
        assert len(source_events) == 1
        assert isinstance(source_events[0]["entries"], list)

    def test_chat_no_messages_returns_400(self, ai_env):
        llm = MockLLMService()
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/chat",
            json={"messages": [], "kb": "test-events"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_REQUEST"

    def test_chat_ai_not_configured(self, ai_env):
        llm = MockLLMService(configured=False)
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/chat",
            json={
                "messages": [{"role": "user", "content": "hello"}],
                "kb": "test-events",
            },
        )
        assert resp.status_code == 503

    def test_chat_with_entry_context(self, ai_env):
        """Chat with entry_id includes entry in context."""
        llm = MockLLMService(stream_tokens=["Response"])
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/chat",
            json={
                "messages": [{"role": "user", "content": "Summarize this"}],
                "kb": "test-events",
                "entry_id": "2025-01-10--test-event-0",
            },
        )
        assert resp.status_code == 200

        events = []
        for line in resp.text.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1

    def test_chat_with_conversation_history(self, ai_env):
        """Chat with multiple messages passes history correctly."""
        llm = MockLLMService(stream_tokens=["Follow-up"])
        _inject_llm(ai_env["app"], llm)
        resp = ai_env["client"].post(
            "/api/ai/chat",
            json={
                "messages": [
                    {"role": "user", "content": "What is immigration policy?"},
                    {"role": "assistant", "content": "Immigration policy is..."},
                    {"role": "user", "content": "Tell me more"},
                ],
                "kb": "test-events",
            },
        )
        assert resp.status_code == 200
        events = []
        for line in resp.text.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        assert any(e["type"] == "done" for e in events)
