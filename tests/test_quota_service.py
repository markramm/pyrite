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
