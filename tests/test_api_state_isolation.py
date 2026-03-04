"""
Tests for API state isolation — app.state replaces module-level globals.

Verifies that each app instance manages its own config/db/services via app.state,
eliminating cross-test contamination from shared module-level singletons.
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB


class TestAppStateIsolation:
    """Verify that create_app stores DI state on app.state, not module globals."""

    def test_two_apps_have_independent_state(self):
        """Two apps created with different configs should not share state."""
        from pyrite.server.api import create_app

        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            d1, d2 = Path(d1), Path(d2)

            kb1 = d1 / "kb"
            kb1.mkdir()
            kb2 = d2 / "kb"
            kb2.mkdir()

            config1 = PyriteConfig(
                knowledge_bases=[KBConfig(name="kb-one", path=kb1, kb_type="generic")],
                settings=Settings(index_path=d1 / "index.db"),
            )
            config2 = PyriteConfig(
                knowledge_bases=[KBConfig(name="kb-two", path=kb2, kb_type="generic")],
                settings=Settings(index_path=d2 / "index.db"),
            )

            app1 = create_app(config=config1)
            app2 = create_app(config=config2)

            # Each app should store its own config on app.state
            assert hasattr(app1.state, "pyrite_config")
            assert hasattr(app2.state, "pyrite_config")
            assert app1.state.pyrite_config is config1
            assert app2.state.pyrite_config is config2

    def test_no_module_level_globals_after_create(self):
        """After create_app, module-level _config/_db/_kb_service should not exist."""
        import pyrite.server.api as api_module
        from pyrite.server.api import create_app

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            kb = d / "kb"
            kb.mkdir()
            config = PyriteConfig(
                knowledge_bases=[KBConfig(name="test", path=kb, kb_type="generic")],
                settings=Settings(index_path=d / "index.db"),
            )
            create_app(config=config)

            # Module globals should not be used for state
            assert not hasattr(api_module, "_config") or api_module._config is None
            assert not hasattr(api_module, "_db") or api_module._db is None
            assert not hasattr(api_module, "_kb_service") or api_module._kb_service is None

    def test_di_overrides_use_app_state(self):
        """DI overrides should resolve config/db from app.state."""
        from pyrite.server.api import create_app, get_config, get_db

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            kb = d / "kb"
            kb.mkdir()
            config = PyriteConfig(
                knowledge_bases=[KBConfig(name="test", path=kb, kb_type="generic")],
                settings=Settings(index_path=d / "index.db"),
            )
            app = create_app(config=config)

            # create_app should have set dependency_overrides for get_config and get_db
            assert get_config in app.dependency_overrides
            assert get_db in app.dependency_overrides

            # The override for get_config should return the same config
            assert app.dependency_overrides[get_config]() is config

            client = TestClient(app)
            # /api/kbs should use the correct config
            resp = client.get("/api/kbs")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["kbs"][0]["name"] == "test"

    def test_invalidate_llm_service_uses_app_state(self):
        """app.state should have a pyrite_llm_service attribute."""
        from pyrite.server.api import create_app

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            kb = d / "kb"
            kb.mkdir()
            config = PyriteConfig(
                knowledge_bases=[KBConfig(name="test", path=kb, kb_type="generic")],
                settings=Settings(index_path=d / "index.db"),
            )
            app = create_app(config=config)
            assert hasattr(app.state, "pyrite_llm_service")

    def test_separate_apps_dont_share_db(self):
        """Each app should get its own DB instance, not a shared module global."""
        from pyrite.server.api import create_app, get_db

        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            d1, d2 = Path(d1), Path(d2)
            for d in (d1, d2):
                (d / "kb").mkdir()

            config1 = PyriteConfig(
                knowledge_bases=[KBConfig(name="kb1", path=d1 / "kb", kb_type="generic")],
                settings=Settings(index_path=d1 / "index.db"),
            )
            config2 = PyriteConfig(
                knowledge_bases=[KBConfig(name="kb2", path=d2 / "kb", kb_type="generic")],
                settings=Settings(index_path=d2 / "index.db"),
            )

            app1 = create_app(config=config1)
            app2 = create_app(config=config2)

            db1 = app1.dependency_overrides[get_db]()
            db2 = app2.dependency_overrides[get_db]()

            # DBs should be different instances pointing to different files
            assert db1 is not db2
