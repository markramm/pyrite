"""Operator settings: admin-only to change, and secrets never read back.

The settings table holds instance-wide configuration, including the AI
provider credential the server uses on the operator's behalf. Two rules:

- Changing an operator setting (the ``ai.*`` family, and any key holding a
  credential) requires the admin tier. A write-role user may still change
  their own UI preferences (``appearance.*``, ``general.*``).
- A secret value is never returned by the settings read endpoints, to
  anyone -- admin included. The read shows a masked indicator instead, and
  the server keeps using the real value.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

SECRET = "sk-operator-secret-value"


@pytest.fixture
def env(tmp_path: Path):
    from pyrite.config import AuthConfig, KBConfig, PyriteConfig
    from pyrite.server.api import create_app
    from pyrite.services.auth_service import AuthService

    kb_path = tmp_path / "notes"
    kb_path.mkdir()
    cfg = PyriteConfig(knowledge_bases=[KBConfig(name="notes", path=kb_path, kb_type="generic")])
    cfg.settings.index_path = tmp_path / "index.db"
    cfg.settings.auth = AuthConfig(enabled=True, allow_registration=True, anonymous_tier="read")
    app = create_app(cfg)

    def login(username: str, role: str | None = None) -> TestClient:
        c = TestClient(app)
        r = c.post("/auth/register", json={"username": username, "password": "password1"})
        assert r.status_code in (200, 201), r.text
        if role is not None:
            AuthService(app.state.pyrite_db, cfg.settings.auth).set_role(r.json()["id"], role)
            c.cookies.clear()
            r = c.post("/auth/login", json={"username": username, "password": "password1"})
            assert r.status_code == 200, r.text
        return c

    admin = login("owner")  # first user is admin
    writer = login("wendy", "write")
    reader = login("rita", "read")
    anon = TestClient(app)
    return SimpleNamespace(app=app, cfg=cfg, admin=admin, writer=writer, reader=reader, anon=anon)


def _seed_secret(env) -> None:
    r = env.admin.put("/api/settings/ai.apiKey", json={"value": SECRET})
    assert r.status_code == 200, r.text


class TestOperatorSettingsNeedAdmin:
    @pytest.mark.parametrize(
        "key", ["ai.apiKey", "ai.baseUrl", "ai.provider", "ai.model", "embedding.apiToken"]
    )
    def test_write_role_cannot_set_operator_setting(self, env, key):
        r = env.writer.put(f"/api/settings/{key}", json={"value": "https://attacker.example"})
        assert r.status_code == 403, r.text
        assert env.app.state.pyrite_db.get_setting(key) is None

    def test_write_role_cannot_bulk_set_operator_setting(self, env):
        r = env.writer.put(
            "/api/settings", json={"settings": {"appearance.theme": "dark", "ai.apiKey": "x"}}
        )
        assert r.status_code == 403, r.text
        db = env.app.state.pyrite_db
        assert db.get_setting("ai.apiKey") is None
        # All-or-nothing: the harmless key in the same request is not applied either.
        assert db.get_setting("appearance.theme") is None

    def test_write_role_cannot_delete_operator_setting(self, env):
        _seed_secret(env)
        r = env.writer.delete("/api/settings/ai.apiKey")
        assert r.status_code == 403, r.text
        assert env.app.state.pyrite_db.get_setting("ai.apiKey") == SECRET

    def test_write_role_can_still_set_preferences(self, env):
        r = env.writer.put("/api/settings/appearance.theme", json={"value": "dark"})
        assert r.status_code == 200, r.text
        r = env.writer.put("/api/settings", json={"settings": {"general.itemsPerPage": "25"}})
        assert r.status_code == 200, r.text

    def test_admin_sets_secret_and_server_uses_it(self, env):
        from pyrite.server.api import get_llm_service

        _seed_secret(env)
        db = env.app.state.pyrite_db
        assert db.get_setting("ai.apiKey") == SECRET
        fake_request = SimpleNamespace(state=SimpleNamespace())
        llm = get_llm_service(fake_request, env.cfg, db)
        assert llm._settings.ai_api_key == SECRET


class TestSecretsNeverReadBack:
    @pytest.mark.parametrize("who", ["anon", "reader", "writer", "admin"])
    def test_get_all_masks_secret(self, env, who):
        _seed_secret(env)
        r = getattr(env, who).get("/api/settings")
        assert r.status_code == 200, r.text
        assert SECRET not in r.text
        body = r.json()
        assert body["settings"]["ai.apiKey"] != SECRET
        assert body["settings"]["ai.apiKey"]  # an indicator that it is set
        assert "ai.apiKey" in body["masked"]

    @pytest.mark.parametrize("who", ["anon", "reader", "writer", "admin"])
    def test_get_one_masks_secret(self, env, who):
        _seed_secret(env)
        r = getattr(env, who).get("/api/settings/ai.apiKey")
        assert r.status_code == 200, r.text
        assert SECRET not in r.text

    def test_unset_secret_reads_as_absent(self, env):
        r = env.anon.get("/api/settings")
        assert "ai.apiKey" not in r.json()["settings"]
        assert env.anon.get("/api/settings/ai.apiKey").json()["value"] is None

    def test_admin_write_response_does_not_echo_secret(self, env):
        r = env.admin.put("/api/settings/ai.apiKey", json={"value": SECRET})
        assert SECRET not in r.text
        r = env.admin.put("/api/settings", json={"settings": {"ai.apiKey": SECRET}})
        assert SECRET not in r.text

    def test_writing_back_the_mask_keeps_the_secret(self, env):
        """A client that saves every field it loaded must not clobber the key."""
        _seed_secret(env)
        masked = env.admin.get("/api/settings").json()["settings"]["ai.apiKey"]
        r = env.admin.put("/api/settings", json={"settings": {"ai.apiKey": masked}})
        assert r.status_code == 200, r.text
        assert env.app.state.pyrite_db.get_setting("ai.apiKey") == SECRET


class TestSecretKeyList:
    def test_explicit_list_names_the_ai_key(self):
        from pyrite.server.endpoints import settings_ep

        assert "ai.apiKey" in settings_ep.SECRET_SETTINGS

    def test_listed_key_is_secret_even_when_the_name_does_not_say_so(self, monkeypatch):
        from pyrite.server.endpoints import settings_ep

        assert not settings_ep.is_secret_setting("ai.orgHandle")
        monkeypatch.setattr(
            settings_ep, "SECRET_SETTINGS", settings_ep.SECRET_SETTINGS | {"ai.orgHandle"}
        )
        assert settings_ep.is_secret_setting("ai.orgHandle")

    def test_name_heuristic_is_the_fallback(self):
        from pyrite.server.endpoints.settings_ep import is_secret_setting

        assert is_secret_setting("embedding.apiToken")
        assert not is_secret_setting("appearance.theme")


BASE_URL = "https://svc-user:url-password@llm.example.com/v1?api_key=url-key-value&region=eu"


class TestBaseUrlCredentials:
    def _seed(self, env):
        r = env.admin.put("/api/settings/ai.baseUrl", json={"value": BASE_URL})
        assert r.status_code == 200, r.text

    @pytest.mark.parametrize("who", ["anon", "reader", "writer"])
    def test_non_admin_never_sees_url_credentials(self, env, who):
        self._seed(env)
        client = getattr(env, who)
        for r in (client.get("/api/settings"), client.get("/api/settings/ai.baseUrl")):
            assert r.status_code == 200, r.text
            for secret in ("url-password", "url-key-value", "svc-user"):
                assert secret not in r.text, (who, r.text)
            assert "llm.example.com" in r.text
            assert "region=eu" in r.text

    def test_admin_sees_the_full_url(self, env):
        self._seed(env)
        assert env.admin.get("/api/settings").json()["settings"]["ai.baseUrl"] == BASE_URL
        assert env.admin.get("/api/settings/ai.baseUrl").json()["value"] == BASE_URL

    def test_plain_url_is_returned_unchanged(self, env):
        env.admin.put("/api/settings/ai.baseUrl", json={"value": "http://localhost:11434/v1"})
        r = env.anon.get("/api/settings/ai.baseUrl")
        assert r.json()["value"] == "http://localhost:11434/v1"
