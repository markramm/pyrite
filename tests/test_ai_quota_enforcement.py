"""Tests for LLM quota enforcement on the AI endpoints
(wire-user-usage-tier-resolution-for-quota-enforcement).

Uses real auth (not the fully-mocked ai_env fixture) so the request
carries a real authenticated user whose usage_tier is resolvable, and
the REAL LLMService (with a mocked Anthropic SDK client, matching
test_llm_service.py's pattern) rather than a hand-rolled mock -- the
quota check depends on LLMService actually recording usage via its
injected usage_service, which a naive mock would silently bypass.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
passlib = pytest.importorskip("passlib", reason="passlib not installed")

from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings, UsageTierConfig
from pyrite.server.api import create_app, get_config, get_db
from pyrite.storage.database import PyriteDB


def _mock_anthropic_module():
    """A mock 'anthropic' module whose client.messages.create() returns a
    minimal, real-shaped response (content + usage), so LLMService's own
    _record_anthropic_usage() path actually records a row."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Mock summary")]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5
    mock_response.usage.cache_creation_input_tokens = 0
    mock_response.usage.cache_read_input_tokens = 0
    mock_client.messages.create = MagicMock(return_value=mock_response)

    mock_module = MagicMock()
    mock_module.Anthropic.return_value = mock_client
    return mock_module


@pytest.fixture
def quota_env():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        db_path = tmpdir / "index.db"
        kb_path = tmpdir / "kb"
        kb_path.mkdir()

        config = PyriteConfig(
            knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
            settings=Settings(
                index_path=db_path,
                ai_provider="anthropic",
                ai_api_key="sk-test",
                ai_model="claude-sonnet-4-20250514",
                auth=AuthConfig(
                    enabled=True,
                    allow_registration=True,
                    usage_tiers={"default": UsageTierConfig(daily_llm_requests=2)},
                ),
            ),
        )

        app = create_app(config=config)
        db = PyriteDB(db_path)
        app.dependency_overrides[get_config] = lambda: config
        app.dependency_overrides[get_db] = lambda: db

        client = TestClient(app)
        client.post("/auth/register", json={"username": "alice", "password": "password123"})

        # Seed one entry to summarize, plus a second so suggest-links has a
        # non-self candidate to find via search.
        from pyrite.models.factory import build_entry
        from pyrite.storage.index import IndexManager
        from pyrite.storage.repository import KBRepository

        entry = build_entry(
            "note",
            entry_id="quota-test-entry",
            title="Quota Test Entry",
            body="Some content to summarize.",
        )
        other_entry = build_entry(
            "note",
            entry_id="quota-test-other-entry",
            title="Quota Test Other Entry",
            body="Some other related content.",
        )
        repo = KBRepository(config.knowledge_bases[0])
        repo.save(entry)
        repo.save(other_entry)
        IndexManager(db, config).index_all()

        yield {"client": client, "config": config, "db": db, "entry_id": entry.id}
        db.close()


class TestAISummarizeQuota:
    def test_under_quota_succeeds(self, quota_env):
        client = quota_env["client"]
        with patch(
            "pyrite.services.llm_service._import_anthropic",
            return_value=_mock_anthropic_module(),
        ):
            response = client.post(
                "/api/ai/summarize", json={"entry_id": quota_env["entry_id"], "kb_name": "test-kb"}
            )
        assert response.status_code == 200

    def test_over_quota_is_denied(self, quota_env):
        client = quota_env["client"]
        entry_id = quota_env["entry_id"]

        with patch(
            "pyrite.services.llm_service._import_anthropic",
            return_value=_mock_anthropic_module(),
        ):
            for _ in range(2):
                r = client.post(
                    "/api/ai/summarize", json={"entry_id": entry_id, "kb_name": "test-kb"}
                )
                assert r.status_code == 200

            third = client.post(
                "/api/ai/summarize", json={"entry_id": entry_id, "kb_name": "test-kb"}
            )
        assert third.status_code == 429
        assert third.json()["detail"]["code"] == "QUOTA_EXCEEDED"


class TestAIAutoTagQuota:
    def test_over_quota_is_denied(self, quota_env):
        client = quota_env["client"]
        entry_id = quota_env["entry_id"]

        with patch(
            "pyrite.services.llm_service._import_anthropic",
            return_value=_mock_anthropic_module(),
        ):
            for _ in range(2):
                r = client.post(
                    "/api/ai/auto-tag", json={"entry_id": entry_id, "kb_name": "test-kb"}
                )
                assert r.status_code == 200

            third = client.post(
                "/api/ai/auto-tag", json={"entry_id": entry_id, "kb_name": "test-kb"}
            )
        assert third.status_code == 429
        assert third.json()["detail"]["code"] == "QUOTA_EXCEEDED"

    def test_usage_is_recorded_with_auto_tag_kind(self, quota_env):
        client = quota_env["client"]
        db = quota_env["db"]
        with patch(
            "pyrite.services.llm_service._import_anthropic",
            return_value=_mock_anthropic_module(),
        ):
            client.post(
                "/api/ai/auto-tag", json={"entry_id": quota_env["entry_id"], "kb_name": "test-kb"}
            )
        rows = db.execute_sql("SELECT kind FROM llm_usage")
        assert len(rows) == 1
        assert rows[0]["kind"] == "auto-tag"


class TestAISuggestLinksQuota:
    def test_over_quota_is_denied(self, quota_env):
        client = quota_env["client"]
        entry_id = quota_env["entry_id"]

        with patch(
            "pyrite.services.llm_service._import_anthropic",
            return_value=_mock_anthropic_module(),
        ):
            for _ in range(2):
                r = client.post(
                    "/api/ai/suggest-links", json={"entry_id": entry_id, "kb_name": "test-kb"}
                )
                assert r.status_code == 200

            third = client.post(
                "/api/ai/suggest-links", json={"entry_id": entry_id, "kb_name": "test-kb"}
            )
        assert third.status_code == 429
        assert third.json()["detail"]["code"] == "QUOTA_EXCEEDED"

    def test_usage_is_recorded_with_suggest_links_kind(self, quota_env):
        client = quota_env["client"]
        db = quota_env["db"]
        with patch(
            "pyrite.services.llm_service._import_anthropic",
            return_value=_mock_anthropic_module(),
        ):
            client.post(
                "/api/ai/suggest-links",
                json={"entry_id": quota_env["entry_id"], "kb_name": "test-kb"},
            )
        rows = db.execute_sql("SELECT kind FROM llm_usage")
        assert len(rows) == 1
        assert rows[0]["kind"] == "suggest-links"


class TestAISummarizeQuotaKindIsolation:
    """A quota scoped to kind='summarize' must be tracked distinctly from
    other kinds -- otherwise recording every call under one hardcoded
    kind would let unrelated endpoints exhaust each other's quota, or
    silently never see their own usage."""

    def test_summarize_usage_is_recorded_with_summarize_kind(self, quota_env):
        client = quota_env["client"]
        db = quota_env["db"]
        with patch(
            "pyrite.services.llm_service._import_anthropic",
            return_value=_mock_anthropic_module(),
        ):
            client.post(
                "/api/ai/summarize", json={"entry_id": quota_env["entry_id"], "kb_name": "test-kb"}
            )
        rows = db.execute_sql("SELECT kind FROM llm_usage")
        assert len(rows) == 1
        assert rows[0]["kind"] == "summarize"
