"""Tests for embedding service pre-warm feature."""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestEmbeddingServicePrewarm:
    """Unit tests for EmbeddingService.prewarm() and is_warm."""

    def test_prewarm_returns_false_when_unavailable(self):
        """prewarm() returns False when sentence-transformers is not installed."""
        from pyrite.services.embedding_service import EmbeddingService

        db = MagicMock()
        svc = EmbeddingService(db)

        with patch("pyrite.services.embedding_service.is_available", return_value=False):
            assert svc.prewarm() is False

    def test_prewarm_returns_true_and_loads_model(self):
        """prewarm() loads the model and returns True."""
        from pyrite.services.embedding_service import EmbeddingService

        db = MagicMock()
        svc = EmbeddingService(db)

        fake_model = MagicMock()
        with (
            patch("pyrite.services.embedding_service.is_available", return_value=True),
            patch.object(svc, "_get_model", return_value=fake_model),
        ):
            assert svc.prewarm() is True

    def test_is_warm_false_initially(self):
        """is_warm is False before prewarm() is called."""
        from pyrite.services.embedding_service import EmbeddingService

        db = MagicMock()
        svc = EmbeddingService(db)
        assert svc.is_warm is False

    def test_is_warm_true_after_prewarm(self):
        """is_warm is True after successful prewarm()."""
        from pyrite.services.embedding_service import EmbeddingService

        db = MagicMock()
        svc = EmbeddingService(db)
        svc._model = MagicMock()  # Simulate loaded model
        assert svc.is_warm is True

    def test_prewarm_returns_false_on_load_failure(self):
        """prewarm() returns False if model loading fails."""
        from pyrite.services.embedding_service import EmbeddingService

        db = MagicMock()
        svc = EmbeddingService(db)

        with (
            patch("pyrite.services.embedding_service.is_available", return_value=True),
            patch.object(svc, "_get_model", side_effect=RuntimeError("model load failed")),
        ):
            assert svc.prewarm() is False


class TestPrewarmEnvOverride:
    """Test PYRITE_PREWARM_EMBEDDINGS env var override."""

    def test_env_override_sets_prewarm(self):
        """PYRITE_PREWARM_EMBEDDINGS=true sets prewarm_embeddings=True."""
        from pyrite.config import _apply_env_overrides, PyriteConfig

        config = PyriteConfig()
        assert config.settings.prewarm_embeddings is False

        with patch.dict(os.environ, {"PYRITE_PREWARM_EMBEDDINGS": "true"}):
            _apply_env_overrides(config)
        assert config.settings.prewarm_embeddings is True

    def test_env_override_false(self):
        """PYRITE_PREWARM_EMBEDDINGS=false leaves prewarm_embeddings=False."""
        from pyrite.config import _apply_env_overrides, PyriteConfig

        config = PyriteConfig()
        with patch.dict(os.environ, {"PYRITE_PREWARM_EMBEDDINGS": "false"}):
            _apply_env_overrides(config)
        assert config.settings.prewarm_embeddings is False


class TestLifespanPrewarm:
    """Test that create_app sets up embedding service on app.state when prewarm enabled."""

    def test_embedding_svc_on_app_state_when_enabled(self):
        """create_app stores EmbeddingService on app.state when prewarm_embeddings=True."""
        from pyrite.config import PyriteConfig
        from pyrite.server.api import create_app

        config = PyriteConfig()
        config.settings.prewarm_embeddings = True
        app = create_app(config)

        svc = getattr(app.state, "pyrite_embedding_svc", None)
        assert svc is not None
        from pyrite.services.embedding_service import EmbeddingService

        assert isinstance(svc, EmbeddingService)

    def test_no_embedding_svc_when_disabled(self):
        """create_app does not create EmbeddingService when prewarm_embeddings=False."""
        from pyrite.config import PyriteConfig
        from pyrite.server.api import create_app

        config = PyriteConfig()
        config.settings.prewarm_embeddings = False
        app = create_app(config)

        svc = getattr(app.state, "pyrite_embedding_svc", None)
        assert svc is None


class TestHealthEndpointEmbeddingStatus:
    """Test /health endpoint includes embedding readiness when configured."""

    def test_health_includes_embeddings_when_prewarm_enabled(self):
        """Health endpoint includes embeddings.ready field when prewarm is configured."""
        from pyrite.config import PyriteConfig
        from pyrite.server.api import create_app, get_config

        config = PyriteConfig()
        config.settings.prewarm_embeddings = True
        app = create_app(config)
        app.dependency_overrides[get_config] = lambda: config

        from starlette.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "embeddings" in data
        assert "ready" in data["embeddings"]

    def test_health_no_embeddings_when_prewarm_disabled(self):
        """Health endpoint omits embeddings field when prewarm is not configured."""
        from pyrite.config import PyriteConfig
        from pyrite.server.api import create_app, get_config

        config = PyriteConfig()
        config.settings.prewarm_embeddings = False
        app = create_app(config)
        app.dependency_overrides[get_config] = lambda: config

        from starlette.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "embeddings" not in data
