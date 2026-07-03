"""Tests for the LLM usage REST endpoints (llm-usage-tracking-and-quotas).

GET /api/usage/me -- current user's usage totals.
GET /api/admin/usage -- admin view across all users.
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app
from pyrite.services.llm_usage_service import LLMUsageService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def usage_client():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        kb = KBConfig(name="test-kb", path=tmpdir / "kb", kb_type="generic")
        (tmpdir / "kb").mkdir()
        config = PyriteConfig(
            knowledge_bases=[kb], settings=Settings(index_path=tmpdir / "index.db")
        )
        db = PyriteDB(config.settings.index_path)
        usage_svc = LLMUsageService(db)
        usage_svc.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=100,
            output_tokens=50,
        )
        usage_svc.record_usage(
            user_id=2,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=200,
            output_tokens=75,
        )

        app = create_app(config=config)
        app.dependency_overrides[__import__("pyrite.server.api", fromlist=["get_db"]).get_db] = (
            lambda: db
        )
        client = TestClient(app)

        yield {"client": client, "db": db}
        db.close()


class TestUsageMeEndpoint:
    def test_no_auth_user_returns_anonymous_usage(self, usage_client):
        """With auth disabled (the test default), there's no authenticated
        user -- the endpoint should return the null-user_id bucket (0
        usage, since our fixture only records usage for users 1 and 2),
        not error."""
        client = usage_client["client"]
        response = client.get("/api/usage/me")
        assert response.status_code == 200
        data = response.json()
        assert "input_tokens" in data
        assert "output_tokens" in data
        assert "request_count" in data


class TestAdminUsageEndpoint:
    def test_returns_per_user_totals(self, usage_client):
        client = usage_client["client"]
        response = client.get("/api/admin/usage")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        by_user = {row["user_id"]: row for row in data["users"]}
        assert by_user[1]["input_tokens"] == 100
        assert by_user[2]["input_tokens"] == 200
