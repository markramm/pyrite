"""Tests for settings system."""

import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


class TestSettingsDB:
    """Tests for settings database operations."""

    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            yield db
            db.close()

    def test_setting_table_exists(self, db):
        """setting table should be created."""
        row = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='setting'"
        ).fetchone()
        assert row is not None

    def test_set_and_get_setting(self, db):
        """Can set and retrieve a setting."""
        db.set_setting("theme", "dark")
        assert db.get_setting("theme") == "dark"

    def test_get_missing_setting_returns_none(self, db):
        """Getting nonexistent setting returns None."""
        assert db.get_setting("nonexistent") is None

    def test_upsert_setting(self, db):
        """Setting same key updates value."""
        db.set_setting("theme", "dark")
        db.set_setting("theme", "light")
        assert db.get_setting("theme") == "light"

    def test_get_all_settings(self, db):
        """get_all_settings returns dict of all settings."""
        db.set_setting("theme", "dark")
        db.set_setting("fontSize", "14")
        settings = db.get_all_settings()
        assert settings == {"theme": "dark", "fontSize": "14"}

    def test_delete_setting(self, db):
        """delete_setting removes setting."""
        db.set_setting("theme", "dark")
        assert db.delete_setting("theme") is True
        assert db.get_setting("theme") is None

    def test_delete_nonexistent_setting(self, db):
        """delete_setting returns False for missing key."""
        assert db.delete_setting("nonexistent") is False

    def test_empty_settings(self, db):
        """get_all_settings returns empty dict when no settings."""
        assert db.get_all_settings() == {}


class TestSettingsAPI:
    """Test settings REST endpoints."""

    @pytest.fixture
    def client(self):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        import pyrite.server.api as api_module
        from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
        from pyrite.server.api import create_app

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "notes"
            kb_path.mkdir()

            kb = KBConfig(name="test", path=kb_path, kb_type=KBType.GENERIC)
            config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=db_path))

            db = PyriteDB(db_path)

            api_module._config = config
            api_module._db = db
            app = create_app(config)
            yield TestClient(app)
            db.close()

    def test_get_settings_empty(self, client):
        """GET /settings returns empty dict initially."""
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        assert resp.json()["settings"] == {}

    def test_set_and_get_setting(self, client):
        """PUT and GET single setting."""
        resp = client.put("/api/settings/theme", json={"value": "dark"})
        assert resp.status_code == 200
        assert resp.json()["value"] == "dark"

        resp = client.get("/api/settings/theme")
        assert resp.status_code == 200
        assert resp.json()["value"] == "dark"

    def test_bulk_update_settings(self, client):
        """PUT /settings bulk update."""
        resp = client.put("/api/settings", json={"settings": {"theme": "light", "fontSize": "16"}})
        assert resp.status_code == 200
        settings = resp.json()["settings"]
        assert settings["theme"] == "light"
        assert settings["fontSize"] == "16"

    def test_delete_setting(self, client):
        """DELETE /settings/{key} removes setting."""
        client.put("/api/settings/theme", json={"value": "dark"})
        resp = client.delete("/api/settings/theme")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_nonexistent_returns_404(self, client):
        """DELETE nonexistent setting returns 404."""
        resp = client.delete("/api/settings/nonexistent")
        assert resp.status_code == 404
