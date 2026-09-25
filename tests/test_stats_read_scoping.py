"""`GET /api/stats` reports only the KBs its caller may read.

The route returned index-wide statistics to every caller: the name and row of
every KB (a private KB's existence is itself private), and totals -- entries,
tags, links, entries per type -- that counted the private KBs' rows. A scoped
caller (a logged-in user, or an anonymous visitor on an auth-enabled instance)
now gets the per-KB map and every total computed from the KBs it may read.
Unscoped callers (a global admin, an operator API key, auth disabled) still
get the index-wide numbers.
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from tests.auth_seed import seed_and_sign_in

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
        # Public: 2 entries, 1 tag, 1 link, types {note: 1, event: 1}.
        svc.create_entry(PUBLIC, "public-note", "Public note", "note", "see [[public-event]]")
        svc.create_entry(
            PUBLIC,
            "public-event",
            "Public event",
            "event",
            "open",
            date="2021-01-01",
            tags=["openly/known"],
        )
        # Private: 3 entries, 2 more tags, 2 more links, and a type the
        # public KB does not have at all.
        svc.create_entry(
            PRIVATE,
            "secret-note",
            "Secret note",
            "note",
            "[[secret-two]] and [[secret-dossier]]",
            tags=["confidential/operation-zebra"],
        )
        svc.create_entry(PRIVATE, "secret-two", "Second secret", "note", "hidden")
        svc.create_entry(
            PRIVATE, "secret-dossier", "Dossier", "dossier", "x", tags=["confidential/source"]
        )

        def client_for(username):
            c = TestClient(app)
            if username:
                r = c.post("/auth/register", json={"username": username, "password": "password123"})
                assert r.status_code == 200, r.text
            return c

        admin = TestClient(app)
        seed_and_sign_in(
            admin, "admin-user", "password123"
        )  # the sole admin, via the operator path
        peer = client_for("peer")
        anon = client_for(None)
        try:
            yield {"admin": admin, "peer": peer, "anon": anon}
        finally:
            db.close()


def _type_counts(body) -> dict[str, int]:
    return {t["entry_type"]: t["count"] for t in body["type_counts"]}


@pytest.mark.parametrize("who", ["peer", "anon"])
def test_scoped_caller_sees_only_readable_kbs_and_their_totals(env, who):
    r = env[who].get("/api/stats")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["kbs"]) == {PUBLIC}
    assert body["total_entries"] == 2
    assert body["total_tags"] == 1
    assert body["total_links"] == 1
    assert _type_counts(body) == {"note": 1, "event": 1}
    assert PRIVATE not in r.text
    assert "dossier" not in r.text


def test_admin_still_sees_the_whole_index(env):
    body = env["admin"].get("/api/stats").json()
    assert set(body["kbs"]) == {PUBLIC, PRIVATE}
    assert body["total_entries"] == 5
    assert body["total_tags"] == 3
    assert body["total_links"] == 3
    assert _type_counts(body) == {"note": 3, "event": 1, "dossier": 1}


def test_unscoped_api_key_caller_is_unchanged(tmp_path):
    """Auth disabled (the default): no identity to scope by, index-wide numbers."""
    (tmp_path / PUBLIC).mkdir()
    (tmp_path / PRIVATE).mkdir()
    config = PyriteConfig(
        knowledge_bases=[
            KBConfig(name=PUBLIC, path=tmp_path / PUBLIC, kb_type="generic"),
            KBConfig(name=PRIVATE, path=tmp_path / PRIVATE, kb_type="generic", default_role="none"),
        ],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    app = create_app(config=config)
    db = PyriteDB(config.settings.index_path)
    try:
        app.dependency_overrides[get_config] = lambda: config
        app.dependency_overrides[get_db] = lambda: db
        svc = KBService(config, db)
        svc.create_entry(PUBLIC, "a", "A", "note", "")
        svc.create_entry(PRIVATE, "b", "B", "note", "")
        body = TestClient(app).get("/api/stats").json()
        assert set(body["kbs"]) == {PUBLIC, PRIVATE}
        assert body["total_entries"] == 2
    finally:
        db.close()
