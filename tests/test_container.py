"""Tests for container-related config: PYRITE_DATA_DIR, env var overrides."""

import os
from unittest.mock import patch

import pytest
from pyrite.config import PyriteConfig, _apply_env_overrides


class TestPyriteDataDir:
    """Tests for PYRITE_DATA_DIR config directory override."""

    def test_pyrite_data_dir_sets_config_dir(self, tmp_path, monkeypatch):
        """PYRITE_DATA_DIR should be used as CONFIG_DIR."""
        data_dir = tmp_path / "mydata"
        data_dir.mkdir()
        monkeypatch.setenv("PYRITE_DATA_DIR", str(data_dir))
        monkeypatch.delenv("PYRITE_CONFIG_DIR", raising=False)

        # CONFIG_DIR is resolve_config_dir() evaluated at import; call it
        # directly. Reloading pyrite.config here used to replace every class
        # in the module (KBConfig, PyriteConfig, ...) for the rest of the
        # worker, so a later test holding the originals saw objects of the
        # "same" class fail isinstance -- an order-dependent failure under -n.
        from pyrite.config import resolve_config_dir

        assert resolve_config_dir() == data_dir.resolve()

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

        with patch.dict(
            os.environ, {"PYRITE_CORS_ORIGINS": "http://a.com, http://b.com,http://c.com"}
        ):
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

    def test_port_env_falls_back_to_platform_port(self):
        """Railway/Heroku inject PORT; honour it when PYRITE_PORT is unset."""
        config = PyriteConfig()
        env_copy = {k: v for k, v in os.environ.items() if k not in ("PYRITE_PORT", "PORT")}
        env_copy["PORT"] = "3000"
        with patch.dict(os.environ, env_copy, clear=True):
            _apply_env_overrides(config)
        assert config.settings.port == 3000

    def test_pyrite_port_wins_over_platform_port(self):
        """Explicit PYRITE_PORT takes precedence over PORT."""
        config = PyriteConfig()
        with patch.dict(os.environ, {"PORT": "3000", "PYRITE_PORT": "9090"}):
            _apply_env_overrides(config)
        assert config.settings.port == 9090

    def test_invalid_port_raises_clear_error(self):
        config = PyriteConfig()
        env_copy = {k: v for k, v in os.environ.items() if k != "PYRITE_PORT"}
        env_copy["PORT"] = "not-a-port"
        with patch.dict(os.environ, env_copy, clear=True):
            with pytest.raises(ValueError, match=r"PORT.*not-a-port"):
                _apply_env_overrides(config)

    def test_invalid_pyrite_port_raises_clear_error(self):
        config = PyriteConfig()
        with patch.dict(os.environ, {"PYRITE_PORT": "80abc"}):
            with pytest.raises(ValueError, match="PYRITE_PORT"):
                _apply_env_overrides(config)

    def test_no_env_keeps_loopback_defaults(self):
        config = PyriteConfig()
        env_copy = {
            k: v for k, v in os.environ.items() if k not in ("PYRITE_HOST", "PYRITE_PORT", "PORT")
        }
        with patch.dict(os.environ, env_copy, clear=True):
            _apply_env_overrides(config)
        assert config.settings.host == "127.0.0.1"
        assert config.settings.port == 8088

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


class TestDockerignoreExcludesNestedNodeModules:
    """`node_modules` must be excluded at every depth, not just the root.

    The frontend stage runs `npm ci` and then `COPY web/ ./`. A host
    `web/node_modules` that reaches the build context overwrites what `npm ci`
    installed, so the image builds against whatever the developer's machine
    happened to have. That was invisible while the two agreed and became a
    hard failure when they diverged:

        Cannot start service: Host version "0.27.3" does not match binary
        version "0.28.2"

    -- the 0.24.3 release build, after esbuild was bumped to 0.28.2 in the
    lockfile while the host tree still had 0.27.3 on disk.
    """

    def _patterns(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        lines = (root / ".dockerignore").read_text().splitlines()
        return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]

    def test_node_modules_is_excluded_at_any_depth(self):
        patterns = self._patterns()
        assert "**/node_modules" in patterns, (
            "`node_modules` alone matches only the context root; web/node_modules "
            "would be copied into the frontend stage and shadow `npm ci`"
        )

    def test_the_root_only_pattern_is_gone(self):
        """A bare `node_modules` beside the recursive one is not wrong, but it
        is the pattern that caused this, so its absence is what we assert."""
        assert "node_modules" not in self._patterns()


class TestDockerfileBindsAllInterfaces:
    def test_dockerfile_sets_pyrite_host(self):
        from pathlib import Path

        dockerfile = Path(__file__).resolve().parent.parent / "Dockerfile"
        contents = dockerfile.read_text()
        assert "ENV PYRITE_HOST=0.0.0.0" in contents
