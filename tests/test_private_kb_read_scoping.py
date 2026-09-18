"""A private KB (default_role "none") must be invisible to users without a grant.

Per-KB roles were enforced on write routes only. Every read route -- entry,
list, search, batch read, graph, KB info -- returned private content to any
logged-in user, and search listed it. On a shared instance whose pilot design
gives peers read access to three named KBs, every other KB is meant to be
private; this is the gap. Operator API keys (no logged-in user) are not scoped:
they are the operator's credential.
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.services.auth_service import AuthService
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB

PUBLIC, PRIVATE = "public-kb", "private-kb"


@pytest.fixture
def env():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / PUBLIC).mkdir()
        (tmp / PRIVATE).mkdir()
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name=PUBLIC, path=tmp / PUBLIC, kb_type="generic", default_role="read"),
                KBConfig(name=PRIVATE, path=tmp / PRIVATE, kb_type="generic", default_role="none"),
            ],
            settings=Settings(
                index_path=tmp / "index.db",
                auth=AuthConfig(enabled=True, allow_registration=True, anonymous_tier="read"),
            ),
        )
        app = create_app(config=config)
        db = PyriteDB(config.settings.index_path)
        app.dependency_overrides[get_config] = lambda: config
        app.dependency_overrides[get_db] = lambda: db
        svc = KBService(config, db)
        svc.create_entry(PUBLIC, "public-note", "Public note", "note", "zebra in the open")
        svc.create_entry(PRIVATE, "secret-note", "Secret note", "note", "zebra behind the wall")
        svc.create_entry(PRIVATE, "secret-two", "Second secret", "note", "another zebra, hidden")

        def client_for(username):
            c = TestClient(app)
            if username:
                r = c.post("/auth/register", json={"username": username, "password": "password123"})
                assert r.status_code == 200, r.text
            return c

        admin = client_for("admin-user")  # first registered user is admin
        peer = client_for("peer")  # second: plain read-tier user
        anon = client_for(None)
        try:
            yield {"admin": admin, "peer": peer, "anon": anon, "db": db, "config": config}
        finally:
            db.close()


def _kb_names(resp):
    return {k["name"] for k in resp.json()["kbs"]}


def _ids(resp, key="entries"):
    body = resp.json()
    items = body.get(key) or body.get("results") or body.get("nodes") or []
    return {i["id"] for i in items}


class TestPeerCannotSeePrivateKB:
    def test_kb_list_hides_private(self, env):
        assert _kb_names(env["peer"].get("/api/kbs")) == {PUBLIC}

    @pytest.mark.parametrize("path", ["", "/schema", "/orient", "/health"])
    def test_kb_detail_routes_are_404_not_403(self, env, path):
        # 404, not 403: a private KB's existence is itself private.
        assert env["peer"].get(f"/api/kbs/{PRIVATE}{path}").status_code == 404
        assert env["peer"].get(f"/api/kbs/{PUBLIC}{path}").status_code == 200

    def test_entry_read_by_id(self, env):
        assert env["peer"].get(f"/api/entries/secret-note?kb={PRIVATE}").status_code == 404
        assert env["peer"].get("/api/entries/secret-note").status_code == 404  # kb omitted
        assert env["peer"].get(f"/api/entries/public-note?kb={PUBLIC}").status_code == 200

    def test_list_scoped_to_private_kb(self, env):
        assert env["peer"].get(f"/api/entries?kb={PRIVATE}").status_code == 404

    def test_list_across_kbs_filters_and_counts_only_readable(self, env):
        r = env["peer"].get("/api/entries")
        assert r.status_code == 200
        assert _ids(r) == {"public-note"}
        assert r.json()["total"] == 1

    def test_search_across_kbs(self, env):
        r = env["peer"].get("/api/search?q=zebra")
        assert r.status_code == 200
        assert _ids(r) == {"public-note"}, r.json()

    def test_search_scoped_to_private_kb(self, env):
        assert env["peer"].get(f"/api/search?q=zebra&kb={PRIVATE}").status_code == 404

    def test_batch_read_reports_private_as_not_found(self, env):
        r = env["peer"].post(
            "/api/entries/batch",
            json={
                "entries": [
                    {"entry_id": "public-note", "kb_name": PUBLIC},
                    {"entry_id": "secret-note", "kb_name": PRIVATE},
                ]
            },
        )
        assert r.status_code == 200
        assert _ids(r) == {"public-note"}
        assert {n["entry_id"] for n in r.json()["not_found"]} == {"secret-note"}

    def test_graph_has_no_private_nodes(self, env):
        r = env["peer"].get("/api/graph")
        assert r.status_code == 200
        assert not {n["id"] for n in r.json()["nodes"]} & {"secret-note", "secret-two"}

    def test_export_of_private_kb(self, env):
        assert env["peer"].get(f"/api/entries/export?kb={PRIVATE}").status_code == 404


class TestWhoCanSee:
    def test_admin_sees_everything(self, env):
        assert _kb_names(env["admin"].get("/api/kbs")) == {PUBLIC, PRIVATE}
        assert _ids(env["admin"].get("/api/search?q=zebra")) == {
            "public-note",
            "secret-note",
            "secret-two",
        }

    def test_anonymous_sees_only_public(self, env):
        assert _kb_names(env["anon"].get("/api/kbs")) == {PUBLIC}
        assert _ids(env["anon"].get("/api/search?q=zebra")) == {"public-note"}

    def test_a_grant_makes_it_visible(self, env):
        auth = AuthService(env["db"], env["config"].settings.auth)
        users = {u["username"]: u for u in auth.list_users()}
        auth.grant_kb_permission(users["peer"]["id"], PRIVATE, "read", users["admin-user"]["id"])
        assert _kb_names(env["peer"].get("/api/kbs")) == {PUBLIC, PRIVATE}
        assert env["peer"].get(f"/api/entries/secret-note?kb={PRIVATE}").status_code == 200
        assert "secret-note" in _ids(env["peer"].get("/api/search?q=zebra"))
