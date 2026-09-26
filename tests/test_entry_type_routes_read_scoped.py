"""#496: the type-list routes are read-scoped.

`GET /api/entries/types` (`list_entry_types`) and `GET /api/entries/type-schemas`
(`list_type_schemas`) both take an optional `kb` and read that KB's content
(`svc.get_distinct_types(kb_name=kb)`, and `kb.yaml` type definitions
respectively) with no auth dependency at all -- unlike every other KB-bearing
route in `entries.py`, which depends on `requires_kb_read()`.

Required property: naming a `kb` the caller cannot read must be refused
exactly as every other entries route refuses it -- 404 KB_NOT_FOUND, the
same body a nonexistent KB gives. With no `kb`, `/api/entries/types`
aggregates distinct types across every KB, so it must be scoped to the
caller's readable KBs the way the other KB-spanning routes are
(`kb_names=readable`, pushed into the query). `/api/entries/type-schemas`
serves no private KB content in its no-`kb` form (core + plugin types only);
its `declared` field only reads a *named* KB's `kb.yaml`, so the no-`kb` case
needs no separate scoping test -- only the guard on `kb`.

Follows the fixture and route conventions in
tests/test_private_kb_read_scoping.py (PUBLIC/PRIVATE KBConfig pair,
seed_and_sign_in for admin/peer/anon).
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
from tests.auth_seed import seed_and_sign_in

PUBLIC, PRIVATE = "public-kb", "private-kb"
NONEXISTENT = "no-such-kb-at-all"

# A type that exists ONLY in the private KB -- proves exclusion from the
# no-kb aggregate, since "note" alone (present in both KBs) would pass even
# with no scoping at all.
PRIVATE_ONLY_TYPE = "secret-only-type"


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
        svc.create_entry(PUBLIC, "public-note", "Public note", "note", "public body")
        svc.create_entry(PRIVATE, "secret-note", "Secret note", "note", "secret body")
        svc.create_entry(
            PRIVATE, "secret-typed", "Secret typed entry", PRIVATE_ONLY_TYPE, "secret typed body"
        )

        def client_for(username):
            c = TestClient(app)
            if username:
                seed_and_sign_in(c, username, "password123", role="read")
            return c

        admin = TestClient(app)
        seed_and_sign_in(admin, "admin-user", "password123", role="admin")
        peer = client_for("peer")
        anon = client_for(None)
        try:
            yield {"admin": admin, "peer": peer, "anon": anon, "db": db, "config": config}
        finally:
            db.close()


def _grant_peer_read_on_private(env):
    auth = AuthService(env["db"], env["config"].settings.auth)
    users = {u["username"]: u for u in auth.list_users()}
    auth.grant_kb_permission(users["peer"]["id"], PRIVATE, "read", users["admin-user"]["id"])


# =============================================================================
# Per-route: anonymous, a reader without access, and a reader with access --
# each against a private KB and a readable one.
# =============================================================================

TYPE_ROUTES = [
    "/api/entries/types?kb={kb}",
    "/api/entries/type-schemas?kb={kb}",
]


@pytest.mark.parametrize("route", TYPE_ROUTES)
class TestNamedPrivateKBIs404:
    @pytest.mark.parametrize("who", ["anon", "peer"])
    def test_private_kb_is_404_not_403(self, env, who, route):
        r = env[who].get(route.format(kb=PRIVATE))
        assert r.status_code == 404, f"{route}: {r.status_code} {r.text[:300]}"
        assert r.json()["detail"]["code"] == "KB_NOT_FOUND"

    @pytest.mark.parametrize("who", ["anon", "peer"])
    def test_private_kb_answers_exactly_as_a_nonexistent_kb(self, env, who, route):
        private = env[who].get(route.format(kb=PRIVATE))
        missing = env[who].get(route.format(kb=NONEXISTENT))
        assert private.status_code == missing.status_code == 404
        normalised = private.text.replace(PRIVATE, "<kb>")
        assert normalised == missing.text.replace(NONEXISTENT, "<kb>"), (
            f"{route}: private KB distinguishable from a nonexistent one\n"
            f"  private: {private.text[:200]}\n  missing: {missing.text[:200]}"
        )

    @pytest.mark.control(
        reason="proves scoping is not a wall for a caller who may read the KB -- "
        "with no auth dependency at all, this route never 404ed anyone, so it "
        "passes both before and after the fix"
    )
    def test_a_reader_with_access_gets_200(self, env, route):
        _grant_peer_read_on_private(env)
        r = env["peer"].get(route.format(kb=PRIVATE))
        assert r.status_code == 200, f"{route}: {r.status_code} {r.text[:300]}"

    @pytest.mark.control(
        reason="a readable KB was never 404ed even with no auth dependency; pins "
        "that adding requires_kb_read() does not start 404ing it"
    )
    def test_readable_kb_is_never_404ed(self, env, route):
        assert env["peer"].get(route.format(kb=PUBLIC)).status_code == 200
        assert env["anon"].get(route.format(kb=PUBLIC)).status_code == 200

    @pytest.mark.control(
        reason="a global admin was never 404ed by these routes before the fix "
        "either; pins that requires_kb_read() does not start walling them off"
    )
    def test_a_global_admin_is_never_404ed(self, env, route):
        r = env["admin"].get(route.format(kb=PRIVATE))
        assert r.status_code != 404 or "KB_NOT_FOUND" not in r.text, (
            f"{route}: scoping 404'd a global admin -- {r.text[:200]}"
        )


@pytest.mark.parametrize("who", ["anon", "peer"])
def test_named_private_kb_types_do_not_leak_before_the_404(env, who):
    """`/api/entries/types?kb=<private>` must never answer with the private
    KB's distinct types -- the 404 from `requires_kb_read()` is what stops
    the body from ever being built from that KB's rows."""
    body = env[who].get(f"/api/entries/types?kb={PRIVATE}").text
    assert PRIVATE_ONLY_TYPE not in body, f"leaked {PRIVATE_ONLY_TYPE}: {body[:300]}"


@pytest.mark.control(
    reason="/api/entries/type-schemas builds its body from CORE_TYPES, plugin "
    "presets and (only when kb is given) that KB's kb.yaml -- never from "
    "DB-indexed entry types -- so a type that exists only as an indexed entry "
    "(PRIVATE_ONLY_TYPE) was never in this route's body even before the fix. "
    "The defect this route has is the missing 404 (test_private_kb_is_404_not_403 "
    "above), not a types leak; this pins that the body stays clean once the "
    "guard also lets a granted caller through."
)
@pytest.mark.parametrize("who", ["anon", "peer"])
def test_named_private_kb_type_schemas_never_carried_the_leak(env, who):
    body = env[who].get(f"/api/entries/type-schemas?kb={PRIVATE}").text
    assert PRIVATE_ONLY_TYPE not in body, f"leaked {PRIVATE_ONLY_TYPE}: {body[:300]}"


# =============================================================================
# The no-`kb` case: /api/entries/types aggregates across every readable KB.
# =============================================================================


@pytest.mark.parametrize("who", ["anon", "peer"])
def test_types_with_no_kb_excludes_private_only_type(env, who):
    r = env[who].get("/api/entries/types")
    assert r.status_code == 200, r.text
    types = set(r.json()["types"])
    assert PRIVATE_ONLY_TYPE not in types, f"private-only type leaked to {who}: {types}"
    assert "note" in types


@pytest.mark.control(
    reason="proves the aggregate scoping follows the grant rather than walling "
    "the KB off entirely; before the fix this route had no scoping at all, so "
    "a granted peer already saw every type"
)
def test_types_with_no_kb_includes_private_type_once_granted(env):
    _grant_peer_read_on_private(env)
    r = env["peer"].get("/api/entries/types")
    assert r.status_code == 200, r.text
    assert PRIVATE_ONLY_TYPE in set(r.json()["types"])


@pytest.mark.control(
    reason="an unscoped admin always saw every KB's types; pins that pushing "
    "kb_names=readable does not change that for a caller readable=None covers"
)
def test_types_with_no_kb_admin_sees_everything(env):
    r = env["admin"].get("/api/entries/types")
    assert r.status_code == 200, r.text
    assert PRIVATE_ONLY_TYPE in set(r.json()["types"])
