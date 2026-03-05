"""Tests for EphemeralKBService (extracted from KBService)."""

import time

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.ephemeral_service import EphemeralKBService
from pyrite.storage.database import PyriteDB


class TestEphemeralKBService:
    """Test ephemeral KB lifecycle via the extracted service."""

    @pytest.fixture
    def svc(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pyrite.config.CONFIG_FILE", tmp_path / "config.yaml")

        config = PyriteConfig(
            settings=Settings(
                index_path=tmp_path / "index.db",
                workspace_path=tmp_path / "workspace",
            ),
        )
        db = PyriteDB(config.settings.index_path)
        service = EphemeralKBService(config, db)
        return service, config, db

    def test_create_ephemeral_kb(self, svc):
        service, config, db = svc
        kb = service.create_ephemeral_kb("test-eph", ttl=3600)
        assert kb.name == "test-eph"
        assert kb.ephemeral is True
        assert kb.ttl == 3600
        assert kb.created_at_ts is not None
        assert kb.path.exists()
        assert config.get_kb("test-eph") is not None

    def test_create_ephemeral_kb_custom_description(self, svc):
        service, config, db = svc
        kb = service.create_ephemeral_kb("desc-eph", ttl=60, description="My temp KB")
        assert kb.description == "My temp KB"

    def test_gc_ephemeral_kbs_removes_expired(self, svc):
        service, config, db = svc
        # Create an ephemeral KB with TTL=1 second
        kb = service.create_ephemeral_kb("expire-me", ttl=1)
        assert kb.path.exists()

        # Wait for expiry
        time.sleep(1.1)

        removed = service.gc_ephemeral_kbs()
        assert "expire-me" in removed
        assert config.get_kb("expire-me") is None
        assert not kb.path.exists()

    def test_gc_ephemeral_kbs_keeps_active(self, svc):
        service, config, db = svc
        service.create_ephemeral_kb("still-alive", ttl=3600)

        removed = service.gc_ephemeral_kbs()
        assert removed == []
        assert config.get_kb("still-alive") is not None
