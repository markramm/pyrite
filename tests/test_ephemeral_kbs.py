"""Tests for ephemeral KB creation and garbage collection."""

import time

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings


class TestEphemeralKBs:
    """Test ephemeral KB lifecycle."""

    @pytest.fixture
    def config_and_svc(self, tmp_path, monkeypatch):
        from pyrite.services.kb_service import KBService
        from pyrite.storage.database import PyriteDB

        # Redirect save_config to tmp_path so tests don't clobber ~/.pyrite/config.yaml
        monkeypatch.setattr("pyrite.config.CONFIG_FILE", tmp_path / "config.yaml")

        config = PyriteConfig(
            settings=Settings(
                index_path=tmp_path / "index.db",
                workspace_path=tmp_path / "workspace",
            ),
        )
        db = PyriteDB(config.settings.index_path)
        svc = KBService(config, db)
        return config, svc, db

    def test_create_ephemeral_kb(self, config_and_svc):
        config, svc, db = config_and_svc
        kb = svc.create_ephemeral_kb("test-eph", ttl=3600)
        assert kb.name == "test-eph"
        assert kb.ephemeral is True
        assert kb.ttl == 3600
        assert kb.created_at_ts is not None
        assert kb.path.exists()
        assert config.get_kb("test-eph") is not None

    def test_gc_removes_expired(self, config_and_svc):
        config, svc, db = config_and_svc
        # Create with already-expired TTL
        kb = svc.create_ephemeral_kb("expired-kb", ttl=1)
        # Backdate the creation time
        kb.created_at_ts = time.time() - 100
        from pyrite.config import save_config

        save_config(config)

        removed = svc.gc_ephemeral_kbs()
        assert "expired-kb" in removed
        assert config.get_kb("expired-kb") is None

    def test_gc_keeps_non_expired(self, config_and_svc):
        config, svc, db = config_and_svc
        svc.create_ephemeral_kb("fresh-kb", ttl=9999)

        removed = svc.gc_ephemeral_kbs()
        assert "fresh-kb" not in removed
        assert config.get_kb("fresh-kb") is not None

    def test_gc_ignores_non_ephemeral(self, config_and_svc, tmp_path):
        config, svc, db = config_and_svc
        # Add a regular KB
        regular_path = tmp_path / "regular"
        regular_path.mkdir()
        config.add_kb(KBConfig(name="regular-kb", path=regular_path))

        removed = svc.gc_ephemeral_kbs()
        assert "regular-kb" not in removed
        assert config.get_kb("regular-kb") is not None

    def test_ephemeral_kb_in_config_roundtrip(self, tmp_path):
        """Test that ephemeral KB fields survive config save/load."""
        config = PyriteConfig(
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        kb = KBConfig(
            name="eph-test",
            path=tmp_path / "eph",
            ephemeral=True,
            ttl=600,
            created_at_ts=1234567890.0,
        )
        (tmp_path / "eph").mkdir()
        config.add_kb(kb)

        # Roundtrip through dict
        data = config.to_dict()
        kb_data = data["knowledge_bases"][0]
        assert kb_data["ephemeral"] is True
        assert kb_data["ttl"] == 600
        assert kb_data["created_at_ts"] == 1234567890.0
