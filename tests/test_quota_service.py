"""Tests for QuotaService (extracted from KBService)."""

import pytest

from pyrite.config import AuthConfig, PyriteConfig, Settings, UsageTierConfig
from pyrite.services.quota_service import QuotaService


class TestQuotaService:
    """Test usage tier limit checking via the extracted service."""

    @pytest.fixture
    def svc_with_tiers(self, tmp_path):
        config = PyriteConfig(
            settings=Settings(
                index_path=tmp_path / "index.db",
                workspace_path=tmp_path / "workspace",
                auth=AuthConfig(
                    usage_tiers={
                        "free": UsageTierConfig(max_personal_kbs=1, max_entries_per_kb=100),
                        "pro": UsageTierConfig(max_personal_kbs=10, max_entries_per_kb=5000),
                    }
                ),
            ),
        )
        return QuotaService(config)

    @pytest.fixture
    def svc_no_tiers(self, tmp_path):
        config = PyriteConfig(
            settings=Settings(
                index_path=tmp_path / "index.db",
                workspace_path=tmp_path / "workspace",
            ),
        )
        return QuotaService(config)

    # -- KB creation checks --

    def test_kb_creation_allowed_within_limit(self, svc_with_tiers):
        allowed, msg = svc_with_tiers.check_kb_creation_allowed(1, "free", 0)
        assert allowed is True
        assert msg == "OK"

    def test_kb_creation_denied_at_limit(self, svc_with_tiers):
        allowed, msg = svc_with_tiers.check_kb_creation_allowed(1, "free", 1)
        assert allowed is False
        assert "KB creation limit reached" in msg

    def test_kb_creation_no_tiers(self, svc_no_tiers):
        allowed, msg = svc_no_tiers.check_kb_creation_allowed(1, "free", 99)
        assert allowed is True
        assert "unlimited" in msg.lower()

    def test_kb_creation_unknown_tier(self, svc_with_tiers):
        allowed, msg = svc_with_tiers.check_kb_creation_allowed(1, "enterprise", 99)
        assert allowed is True
        assert "not found" in msg.lower()

    # -- Entry creation checks --

    def test_entry_creation_allowed_within_limit(self, svc_with_tiers):
        allowed, msg = svc_with_tiers.check_entry_creation_allowed("my-kb", "free", 50)
        assert allowed is True
        assert msg == "OK"

    def test_entry_creation_denied_at_limit(self, svc_with_tiers):
        allowed, msg = svc_with_tiers.check_entry_creation_allowed("my-kb", "free", 100)
        assert allowed is False
        assert "Entry limit reached" in msg

    def test_entry_creation_no_tiers(self, svc_no_tiers):
        allowed, msg = svc_no_tiers.check_entry_creation_allowed("my-kb", "free", 999)
        assert allowed is True
        assert "unlimited" in msg.lower()

    def test_entry_creation_unknown_tier(self, svc_with_tiers):
        allowed, msg = svc_with_tiers.check_entry_creation_allowed("my-kb", "enterprise", 999)
        assert allowed is True
        assert "not found" in msg.lower()

    # -- LLM quota checks (llm-usage-tracking-and-quotas) --

    def test_llm_quota_no_tiers_is_unlimited(self, svc_no_tiers, tmp_path):
        from pyrite.services.llm_usage_service import LLMUsageService
        from pyrite.storage.database import PyriteDB

        db = PyriteDB(tmp_path / "quota-index.db")
        usage_svc = LLMUsageService(db)
        allowed, msg = svc_no_tiers.check_llm_quota(
            user_id=1, kind="chat", user_tier="free", usage_service=usage_svc
        )
        assert allowed is True
        assert "unlimited" in msg.lower()
        db.close()

    def test_llm_quota_unknown_tier_is_unlimited(self, svc_with_tiers, tmp_path):
        from pyrite.services.llm_usage_service import LLMUsageService
        from pyrite.storage.database import PyriteDB

        db = PyriteDB(tmp_path / "quota-index.db")
        usage_svc = LLMUsageService(db)
        allowed, msg = svc_with_tiers.check_llm_quota(
            user_id=1, kind="chat", user_tier="enterprise", usage_service=usage_svc
        )
        assert allowed is True
        assert "not found" in msg.lower()
        db.close()

    def test_llm_quota_tier_without_daily_limit_is_unlimited(self, svc_with_tiers, tmp_path):
        """A tier that doesn't set daily_llm_requests (the default) has
        no LLM quota, even though it has KB/entry limits configured."""
        from pyrite.services.llm_usage_service import LLMUsageService
        from pyrite.storage.database import PyriteDB

        db = PyriteDB(tmp_path / "quota-index.db")
        usage_svc = LLMUsageService(db)
        allowed, msg = svc_with_tiers.check_llm_quota(
            user_id=1, kind="chat", user_tier="free", usage_service=usage_svc
        )
        assert allowed is True
        db.close()

    def test_llm_quota_under_limit_is_allowed(self, tmp_path):
        from pyrite.config import AuthConfig, PyriteConfig, Settings, UsageTierConfig
        from pyrite.services.llm_usage_service import LLMUsageService
        from pyrite.services.quota_service import QuotaService
        from pyrite.storage.database import PyriteDB

        config = PyriteConfig(
            settings=Settings(
                index_path=tmp_path / "index.db",
                workspace_path=tmp_path / "workspace",
                auth=AuthConfig(usage_tiers={"free": UsageTierConfig(daily_llm_requests=10)}),
            ),
        )
        svc = QuotaService(config)
        db = PyriteDB(tmp_path / "quota-index.db")
        usage_svc = LLMUsageService(db)
        for _ in range(3):
            usage_svc.record_usage(
                user_id=1, provider="anthropic", model="x", input_tokens=1, output_tokens=1
            )

        allowed, msg = svc.check_llm_quota(
            user_id=1, kind="chat", user_tier="free", usage_service=usage_svc
        )
        assert allowed is True
        db.close()

    def test_llm_quota_over_limit_is_denied(self, tmp_path):
        from pyrite.config import AuthConfig, PyriteConfig, Settings, UsageTierConfig
        from pyrite.services.llm_usage_service import LLMUsageService
        from pyrite.services.quota_service import QuotaService
        from pyrite.storage.database import PyriteDB

        config = PyriteConfig(
            settings=Settings(
                index_path=tmp_path / "index.db",
                workspace_path=tmp_path / "workspace",
                auth=AuthConfig(usage_tiers={"free": UsageTierConfig(daily_llm_requests=3)}),
            ),
        )
        svc = QuotaService(config)
        db = PyriteDB(tmp_path / "quota-index.db")
        usage_svc = LLMUsageService(db)
        for _ in range(3):
            usage_svc.record_usage(
                user_id=1, provider="anthropic", model="x", input_tokens=1, output_tokens=1
            )

        allowed, msg = svc.check_llm_quota(
            user_id=1, kind="chat", user_tier="free", usage_service=usage_svc
        )
        assert allowed is False
        assert "quota" in msg.lower()
        db.close()
