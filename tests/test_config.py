"""
Tests for multi-KB configuration system.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from pyrite.config import (
    KBConfig,
    KBType,
    PyriteConfig,
    Settings,
    Subscription,
    auto_discover_kbs,
    load_config,
    save_config,
)


class TestKBConfig:
    """Tests for KBConfig."""

    def test_create_kb_config(self):
        """Test creating a KB configuration."""
        kb = KBConfig(
            name="test-kb", path=Path("/tmp/test"), kb_type=KBType.RESEARCH, description="Test KB"
        )
        assert kb.name == "test-kb"
        assert kb.kb_type == KBType.RESEARCH
        # macOS resolves /tmp to /private/tmp
        assert kb.path.name == "test"
        assert kb.path.is_absolute()

    def test_kb_type_from_string(self):
        """Test KB type can be created from string."""
        kb = KBConfig(
            name="test",
            path=Path("/tmp"),
            kb_type="events",  # type: ignore
        )
        assert kb.kb_type == KBType.EVENTS

    def test_path_expansion(self):
        """Test that paths are expanded."""
        kb = KBConfig(name="test", path=Path("~/test"), kb_type=KBType.RESEARCH)
        assert not str(kb.path).startswith("~")
        assert kb.path.is_absolute()

    def test_local_db_path(self):
        """Test local DB path generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KBConfig(name="test", path=Path(tmpdir), kb_type=KBType.RESEARCH)
            db_path = kb.local_db_path
            assert db_path.name == "index.db"
            assert ".pyrite" in str(db_path)

    def test_validation_missing_path(self):
        """Test validation catches missing path."""
        kb = KBConfig(name="test", path=Path("/nonexistent/path"), kb_type=KBType.RESEARCH)
        errors = kb.validate()
        assert len(errors) > 0
        assert "does not exist" in errors[0]


class TestPyriteConfig:
    """Tests for PyriteConfig."""

    def test_create_empty_config(self):
        """Test creating empty config."""
        config = PyriteConfig()
        assert config.version == "1.0"
        assert len(config.knowledge_bases) == 0
        assert config.settings is not None

    def test_add_kb(self):
        """Test adding a KB."""
        config = PyriteConfig()
        kb = KBConfig(name="test", path=Path("/tmp/test"), kb_type=KBType.RESEARCH)
        config.add_kb(kb)
        assert config.get_kb("test") == kb

    def test_add_duplicate_kb_raises(self):
        """Test adding duplicate KB raises error."""
        config = PyriteConfig()
        kb1 = KBConfig(name="test", path=Path("/tmp/1"), kb_type=KBType.RESEARCH)
        kb2 = KBConfig(name="test", path=Path("/tmp/2"), kb_type=KBType.RESEARCH)
        config.add_kb(kb1)
        with pytest.raises(ValueError):
            config.add_kb(kb2)

    def test_remove_kb(self):
        """Test removing a KB."""
        config = PyriteConfig()
        kb = KBConfig(name="test", path=Path("/tmp/test"), kb_type=KBType.RESEARCH)
        config.add_kb(kb)
        assert config.remove_kb("test") is True
        assert config.get_kb("test") is None

    def test_list_kbs_by_type(self):
        """Test listing KBs by type."""
        config = PyriteConfig()
        config.add_kb(KBConfig(name="events1", path=Path("/tmp/1"), kb_type=KBType.EVENTS))
        config.add_kb(KBConfig(name="research1", path=Path("/tmp/2"), kb_type=KBType.RESEARCH))
        config.add_kb(KBConfig(name="research2", path=Path("/tmp/3"), kb_type=KBType.RESEARCH))

        events = config.list_kbs(KBType.EVENTS)
        research = config.list_kbs(KBType.RESEARCH)

        assert len(events) == 1
        assert len(research) == 2

    def test_to_dict_and_from_dict(self):
        """Test serialization roundtrip."""
        config = PyriteConfig()
        config.add_kb(
            KBConfig(
                name="test", path=Path("/tmp/test"), kb_type=KBType.RESEARCH, description="Test KB"
            )
        )
        config.subscriptions.append(
            Subscription(url="git@github.com:test/repo.git", local_path=Path("/tmp/sub"))
        )

        data = config.to_dict()
        restored = PyriteConfig.from_dict(data)

        assert len(restored.knowledge_bases) == 1
        assert restored.get_kb("test").description == "Test KB"
        assert len(restored.subscriptions) == 1


class TestConfigPersistence:
    """Tests for config file persistence."""

    def test_save_and_load(self):
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            os.environ["CASCADE_CONFIG_DIR"] = tmpdir

            # Reload the module to pick up new env var
            from pyrite import config as config_module

            config_module.CONFIG_DIR = Path(tmpdir)
            config_module.CONFIG_FILE = Path(tmpdir) / "config.yaml"

            # Create and save config
            cfg = PyriteConfig()
            cfg.add_kb(
                KBConfig(name="test", path=Path(tmpdir) / "test-kb", kb_type=KBType.RESEARCH)
            )
            save_config(cfg)

            # Verify file exists
            assert (Path(tmpdir) / "config.yaml").exists()

            # Load and verify
            loaded = load_config()
            assert loaded.get_kb("test") is not None


class TestAutoDiscovery:
    """Tests for KB auto-discovery."""

    def test_discover_kb_yaml(self):
        """Test discovering KB from kb.yaml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a kb.yaml
            kb_dir = Path(tmpdir) / "my-research"
            kb_dir.mkdir()
            kb_yaml = kb_dir / "kb.yaml"
            kb_yaml.write_text(
                yaml.safe_dump(
                    {
                        "name": "discovered-kb",
                        "kb_type": "research",
                        "description": "Auto-discovered",
                    }
                )
            )

            discovered = auto_discover_kbs([Path(tmpdir)])

            assert len(discovered) == 1
            assert discovered[0].name == "discovered-kb"
            assert discovered[0].kb_type == KBType.RESEARCH


class TestSettings:
    """Tests for Settings."""

    def test_default_settings(self):
        """Test default settings."""
        settings = Settings()
        assert settings.ai_provider == "stub"
        assert settings.summary_length == 280
        assert settings.enable_mcp is True

    def test_index_path_expansion(self):
        """Test index path is expanded."""
        settings = Settings()
        assert settings.index_path.is_absolute()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
