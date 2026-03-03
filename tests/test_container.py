"""Tests for container-related config: PYRITE_DATA_DIR, env var overrides."""

import os
from unittest.mock import patch

from pyrite.config import PyriteConfig, _apply_env_overrides


class TestPyriteDataDir:
    """Tests for PYRITE_DATA_DIR config directory override."""

    def test_pyrite_data_dir_sets_config_dir(self, tmp_path, monkeypatch):
        """PYRITE_DATA_DIR should be used as CONFIG_DIR."""
        data_dir = tmp_path / "mydata"
        data_dir.mkdir()
        monkeypatch.setenv("PYRITE_DATA_DIR", str(data_dir))
        monkeypatch.delenv("PYRITE_CONFIG_DIR", raising=False)

        # Re-import to pick up the new env var
        import importlib

        import pyrite.config as cfg_mod

        importlib.reload(cfg_mod)
        try:
            assert cfg_mod.CONFIG_DIR == data_dir.resolve()
        finally:
            # Restore original module state
            monkeypatch.delenv("PYRITE_DATA_DIR", raising=False)
            importlib.reload(cfg_mod)

    def test_pyrite_data_dir_sets_index_and_workspace(self, tmp_path):
        """When PYRITE_DATA_DIR is set, index_path and workspace_path should be inside it."""
        config = PyriteConfig()
        data_dir = tmp_path / "data"

        with patch.dict(os.environ, {"PYRITE_DATA_DIR": str(data_dir)}):
            _apply_env_overrides(config)

        assert config.settings.index_path == (data_dir / "index.db").resolve()
        assert config.settings.workspace_path == (data_dir / "repos").resolve()


class TestEnvOverrides:
    """Tests for PYRITE_* environment variable overrides."""

    def test_env_host_port_override(self):
        config = PyriteConfig()
        assert config.settings.host == "127.0.0.1"
        assert config.settings.port == 8088

        with patch.dict(os.environ, {"PYRITE_HOST": "0.0.0.0", "PYRITE_PORT": "9000"}):
            _apply_env_overrides(config)

        assert config.settings.host == "0.0.0.0"
        assert config.settings.port == 9000

    def test_env_auth_enabled_override(self):
        config = PyriteConfig()
        assert config.settings.auth.enabled is False

        with patch.dict(os.environ, {"PYRITE_AUTH_ENABLED": "true"}):
            _apply_env_overrides(config)

        assert config.settings.auth.enabled is True

    def test_env_auth_enabled_false(self):
        config = PyriteConfig()
        config.settings.auth.enabled = True

        with patch.dict(os.environ, {"PYRITE_AUTH_ENABLED": "false"}):
            _apply_env_overrides(config)

        assert config.settings.auth.enabled is False

    def test_env_cors_origins_comma_separated(self):
        config = PyriteConfig()

        with patch.dict(os.environ, {"PYRITE_CORS_ORIGINS": "http://a.com, http://b.com,http://c.com"}):
            _apply_env_overrides(config)

        assert config.settings.cors_origins == ["http://a.com", "http://b.com", "http://c.com"]

    def test_env_overrides_do_not_clobber_explicit_config_values(self):
        """Env vars only apply when set; unset vars leave config alone."""
        config = PyriteConfig()
        config.settings.host = "custom-host"
        config.settings.port = 1234

        # No PYRITE_HOST or PYRITE_PORT in env
        with patch.dict(os.environ, {}, clear=False):
            # Remove any PYRITE_ vars that might be in the real env
            env_copy = {k: v for k, v in os.environ.items() if not k.startswith("PYRITE_")}
            with patch.dict(os.environ, env_copy, clear=True):
                _apply_env_overrides(config)

        assert config.settings.host == "custom-host"
        assert config.settings.port == 1234

    def test_env_ai_provider_override(self):
        config = PyriteConfig()
        assert config.settings.ai_provider == "stub"

        with patch.dict(os.environ, {"PYRITE_AI_PROVIDER": "anthropic"}):
            _apply_env_overrides(config)

        assert config.settings.ai_provider == "anthropic"

    def test_env_api_key_override(self):
        config = PyriteConfig()

        with patch.dict(os.environ, {"PYRITE_API_KEY": "secret-key-123"}):
            _apply_env_overrides(config)

        assert config.settings.api_key == "secret-key-123"

    def test_env_search_mode_override(self):
        config = PyriteConfig()

        with patch.dict(os.environ, {"PYRITE_SEARCH_MODE": "hybrid"}):
            _apply_env_overrides(config)

        assert config.settings.search_mode == "hybrid"

    def test_env_allow_registration_override(self):
        config = PyriteConfig()
        assert config.settings.auth.allow_registration is True

        with patch.dict(os.environ, {"PYRITE_AUTH_ALLOW_REGISTRATION": "false"}):
            _apply_env_overrides(config)

        assert config.settings.auth.allow_registration is False

    def test_env_anonymous_tier_override(self):
        config = PyriteConfig()
        assert config.settings.auth.anonymous_tier is None

        with patch.dict(os.environ, {"PYRITE_AUTH_ANONYMOUS_TIER": "read"}):
            _apply_env_overrides(config)

        assert config.settings.auth.anonymous_tier == "read"

    def test_load_config_applies_env_overrides(self, tmp_path, monkeypatch):
        """load_config() should call _apply_env_overrides."""
        monkeypatch.setenv("PYRITE_HOST", "0.0.0.0")
        monkeypatch.setenv("PYRITE_PORT", "9999")

        import pyrite.config as cfg_mod

        # Point config dir to tmp so we get a default config
        monkeypatch.setattr(cfg_mod, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / "config.yaml")

        config = cfg_mod.load_config()
        assert config.settings.host == "0.0.0.0"
        assert config.settings.port == 9999
