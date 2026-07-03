"""Tests for LLMUsageService — per-user LLM usage tracking and quota
enforcement (llm-usage-tracking-and-quotas).

pyrite/services/llm_service.py makes provider calls without recording
token usage, cost, or which user initiated the request -- no way to
enforce a per-tier quota, see who's burning tokens, or bill back costs.
This service is the recording + quota-check layer; LLMService wires
into it separately.
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.services.llm_usage_service import LLMUsageService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def usage_env():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "index.db"
        db = PyriteDB(db_path)
        service = LLMUsageService(db)
        yield service, db


class TestRecordUsage:
    def test_record_creates_a_usage_row(self, usage_env):
        service, db = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            kind="chat",
            input_tokens=100,
            output_tokens=50,
        )
        rows = db.execute_sql("SELECT * FROM llm_usage WHERE user_id = 1")
        assert len(rows) == 1
        assert rows[0]["provider"] == "anthropic"
        assert rows[0]["model"] == "claude-sonnet-5"
        assert rows[0]["kind"] == "chat"
        assert rows[0]["input_tokens"] == 100
        assert rows[0]["output_tokens"] == 50

    def test_record_defaults_cache_tokens_to_zero(self, usage_env):
        service, db = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=10,
            output_tokens=5,
        )
        rows = db.execute_sql("SELECT * FROM llm_usage WHERE user_id = 1")
        assert rows[0]["cache_read_tokens"] == 0
        assert rows[0]["cache_creation_tokens"] == 0

    def test_record_stores_cache_tokens_when_given(self, usage_env):
        service, db = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=10,
            output_tokens=5,
            cache_read_tokens=200,
            cache_creation_tokens=30,
        )
        rows = db.execute_sql("SELECT * FROM llm_usage WHERE user_id = 1")
        assert rows[0]["cache_read_tokens"] == 200
        assert rows[0]["cache_creation_tokens"] == 30

    def test_record_allows_null_user_id_for_anonymous_or_stub(self, usage_env):
        """Anonymous access (auth disabled) or the stub provider still
        record usage rows -- user_id is nullable, not a hard requirement."""
        service, db = usage_env
        service.record_usage(
            user_id=None, provider="stub", model="stub", input_tokens=0, output_tokens=0
        )
        rows = db.execute_sql("SELECT * FROM llm_usage WHERE provider = 'stub'")
        assert len(rows) == 1
        assert rows[0]["user_id"] is None

    def test_record_computes_estimated_cost(self, usage_env):
        """Cost estimation uses a model->price-per-million-tokens table.
        claude-sonnet-5 is priced (see PRICING) -- verify a known input/
        output combination produces a non-zero, plausible cost."""
        service, db = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        rows = db.execute_sql("SELECT * FROM llm_usage WHERE user_id = 1")
        assert rows[0]["estimated_cost_usd"] > 0

    def test_record_unknown_model_costs_zero_not_an_error(self, usage_env):
        """An unpriced model (e.g. a new release not yet in the pricing
        table) should not raise -- cost estimation is best-effort."""
        service, db = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="some-brand-new-model-2099",
            input_tokens=1000,
            output_tokens=1000,
        )
        rows = db.execute_sql("SELECT * FROM llm_usage WHERE user_id = 1")
        assert rows[0]["estimated_cost_usd"] == 0


class TestGetUsage:
    def test_get_usage_for_user_sums_tokens_and_cost(self, usage_env):
        service, _ = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=100,
            output_tokens=50,
        )
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=200,
            output_tokens=75,
        )
        usage = service.get_usage(user_id=1)
        assert usage["input_tokens"] == 300
        assert usage["output_tokens"] == 125
        assert usage["request_count"] == 2

    def test_get_usage_scopes_to_requested_user_only(self, usage_env):
        service, _ = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=100,
            output_tokens=50,
        )
        service.record_usage(
            user_id=2,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=999,
            output_tokens=999,
        )
        usage = service.get_usage(user_id=1)
        assert usage["input_tokens"] == 100

    def test_get_usage_for_user_with_no_records_is_zero(self, usage_env):
        service, _ = usage_env
        usage = service.get_usage(user_id=999)
        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["request_count"] == 0

    def test_get_all_usage_returns_per_user_totals(self, usage_env):
        service, _ = usage_env
        service.record_usage(
            user_id=1,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=100,
            output_tokens=50,
        )
        service.record_usage(
            user_id=2,
            provider="anthropic",
            model="claude-sonnet-5",
            input_tokens=200,
            output_tokens=75,
        )
        all_usage = service.get_all_usage()
        by_user = {row["user_id"]: row for row in all_usage}
        assert by_user[1]["input_tokens"] == 100
        assert by_user[2]["input_tokens"] == 200


class TestQuota:
    def test_no_quota_configured_is_always_allowed(self, usage_env):
        service, _ = usage_env
        allowed, msg = service.check_quota(user_id=1, kind="chat", daily_limit=None)
        assert allowed is True

    def test_under_quota_is_allowed(self, usage_env):
        service, _ = usage_env
        for _ in range(3):
            service.record_usage(
                user_id=1,
                provider="anthropic",
                model="claude-sonnet-5",
                input_tokens=1,
                output_tokens=1,
                kind="chat",
            )
        allowed, msg = service.check_quota(user_id=1, kind="chat", daily_limit=10)
        assert allowed is True

    def test_over_quota_is_denied(self, usage_env):
        service, _ = usage_env
        for _ in range(10):
            service.record_usage(
                user_id=1,
                provider="anthropic",
                model="claude-sonnet-5",
                input_tokens=1,
                output_tokens=1,
                kind="chat",
            )
        allowed, msg = service.check_quota(user_id=1, kind="chat", daily_limit=10)
        assert allowed is False
        assert "10" in msg

    def test_quota_is_scoped_by_kind(self, usage_env):
        """A user at their 'chat' quota should still be allowed to make
        a 'summarize' request -- quotas are per-kind, not global."""
        service, _ = usage_env
        for _ in range(10):
            service.record_usage(
                user_id=1,
                provider="anthropic",
                model="claude-sonnet-5",
                input_tokens=1,
                output_tokens=1,
                kind="chat",
            )
        allowed, _ = service.check_quota(user_id=1, kind="summarize", daily_limit=10)
        assert allowed is True

    def test_quota_only_counts_todays_requests(self, usage_env):
        """A quota window is rolling/daily -- requests from a prior day
        must not count against today's limit."""
        service, db = usage_env
        db.execute_write_sql(
            """INSERT INTO llm_usage
               (user_id, provider, model, kind, input_tokens, output_tokens, created_at)
               VALUES (1, 'anthropic', 'claude-sonnet-5', 'chat', 1, 1, datetime('now', '-2 days'))"""
        )
        allowed, _ = service.check_quota(user_id=1, kind="chat", daily_limit=1)
        assert allowed is True
