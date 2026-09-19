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
        # A tagged, dated event in each KB, so the timeline, tag and QA
        # routes have something to leak (and something legitimate to show).
        svc.create_entry(
            PUBLIC,
            "public-event",
            "Public event",
            "event",
            "a zebra was seen",
            date="2021-01-01",
            importance=5,
            tags=["openly/known"],
        )
        svc.create_entry(
            PRIVATE,
            "secret-event",
            "Secret event",
            "event",
            "a zebra was smuggled",
            date="2021-06-15",
            importance=7,
            tags=["confidential/operation-zebra"],
        )

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
        assert _ids(r) == {"public-note", "public-event"}
        assert r.json()["total"] == 2

    def test_search_across_kbs(self, env):
        r = env["peer"].get("/api/search?q=zebra")
        assert r.status_code == 200
        assert _ids(r) == {"public-note", "public-event"}, r.json()

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


# =============================================================================
# Every content route (part 1 of the read-scoping work)
#
# The structural test (tests/test_read_scoping_is_structural.py) proves a
# scoping dependency is *declared*. These prove it *works*: no private id,
# title, tag, body text or KB name reaches a caller without a grant.
# =============================================================================

# Content of the private KB: never in any response to a caller without a
# grant, on any route.
PRIVATE_MARKERS = (
    "secret-note",
    "secret-two",
    "secret-event",
    "Secret note",
    "Second secret",
    "Secret event",
    "behind the wall",
    "another zebra, hidden",
    "smuggled",
    "confidential/operation-zebra",
)

# The KB's *name* is separate. On a KB-spanning route it must not appear:
# its presence would disclose that the KB exists. On a route where the
# caller named it themselves, the KB_NOT_FOUND body echoes it back --
# which discloses nothing, because a KB that does not exist echoes it in
# exactly the same body (test_private_kb_answers_exactly_as_a_nonexistent_kb).
PRIVATE_KB_NAME = PRIVATE

NONEXISTENT = "no-such-kb-at-all"

# Routes that name a KB: a private KB must answer exactly as a
# nonexistent one does -- 404 KB_NOT_FOUND, same status, same body.
KB_NAMED_ROUTES = [
    "/api/tags?kb={kb}",
    "/api/tags/tree?kb={kb}",
    "/api/timeline?kb={kb}",
    "/api/qa/status?kb={kb}",
    "/api/qa/validate?kb={kb}",
    "/api/qa/validate/secret-note?kb={kb}",
    "/api/qa/coverage?kb={kb}",
    "/api/entries/secret-note/versions?kb={kb}",
    "/api/entries/secret-note/versions/deadbeef?kb={kb}",
    "/api/entries/secret-note/blocks?kb={kb}",
    "/api/daily/dates?kb={kb}",
    "/api/daily/2021-06-15?kb={kb}",
    "/api/collections?kb={kb}",
    "/api/collections/secret-note?kb={kb}",
    "/api/collections/secret-note/entries?kb={kb}",
    "/api/tasks?kb={kb}",
    "/api/starred?kb={kb}",
    "/api/kbs/{kb}/templates",
    "/api/kbs/{kb}/templates/daily",
    "/api/reviews?entry_id=secret-note&kb_name={kb}",
    "/api/reviews/latest?entry_id=secret-note&kb_name={kb}",
    "/api/reviews/status?entry_id=secret-note&kb_name={kb}",
]

# Routes that span every KB: the response must contain nothing private,
# and its count/total must not include private rows.
KB_SPANNING_ROUTES = [
    "/api/tags",
    "/api/tags/tree",
    "/api/timeline",
    "/api/qa/status",
    "/api/qa/validate",
    "/api/collections",
    "/api/tasks",
    "/api/starred",
]


def _body_text(resp) -> str:
    return resp.text


@pytest.mark.parametrize("who", ["peer", "anon"])
@pytest.mark.parametrize("route", KB_NAMED_ROUTES)
class TestNamedPrivateKBIs404:
    def test_private_kb_is_404_not_403(self, env, who, route):
        r = env[who].get(route.format(kb=PRIVATE))
        assert r.status_code == 404, f"{route} returned {r.status_code}: {r.text[:300]}"

    def test_private_kb_answers_exactly_as_a_nonexistent_kb(self, env, who, route):
        """A private KB's *existence* is private too.

        The two responses must be identical once the KB name the caller
        supplied is normalised out -- that name is the caller's own input
        echoed back, and it appears in both. Anything else differing
        (status, code, message shape, extra fields) would let a caller
        distinguish "you may not read this" from "this does not exist",
        which is the whole point of answering 404 rather than 403.
        """
        private = env[who].get(route.format(kb=PRIVATE))
        missing = env[who].get(route.format(kb=NONEXISTENT))
        assert private.status_code == missing.status_code == 404
        normalised = private.text.replace(PRIVATE, "<kb>")
        assert normalised == missing.text.replace(NONEXISTENT, "<kb>"), (
            f"{route}: private KB distinguishable from a nonexistent one\n"
            f"  private: {private.text[:200]}\n  missing: {missing.text[:200]}"
        )

    def test_no_private_content_in_the_body(self, env, who, route):
        """No id, title, body text or tag from the private KB. The KB name
        the caller supplied may be echoed -- see PRIVATE_KB_NAME."""
        body = _body_text(env[who].get(route.format(kb=PRIVATE)))
        leaked = [m for m in PRIVATE_MARKERS if m in body]
        assert not leaked, f"{route} leaked {leaked} in: {body[:300]}"


@pytest.mark.parametrize("who", ["peer", "anon"])
@pytest.mark.parametrize("route", KB_SPANNING_ROUTES)
class TestKBSpanningRoutesFilterToReadable:
    def test_ok_and_nothing_private(self, env, who, route):
        """Here the KB name is a leak too: the caller never named it, so
        its appearance would disclose that the KB exists at all."""
        r = env[who].get(route)
        assert r.status_code == 200, f"{route} returned {r.status_code}: {r.text[:300]}"
        leaked = [m for m in (*PRIVATE_MARKERS, PRIVATE_KB_NAME) if m in r.text]
        assert not leaked, f"{route} leaked {leaked} in: {r.text[:400]}"


@pytest.mark.parametrize("who", ["peer", "anon"])
class TestCountsDoNotRevealPrivateRows:
    """A count of 3 for rows you cannot see is still a leak."""

    def test_timeline_count_excludes_private_events(self, env, who):
        r = env[who].get("/api/timeline")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == len(body["events"]) == 1
        assert {e["id"] for e in body["events"]} == {"public-event"}

    def test_tags_count_excludes_private_tags(self, env, who):
        r = env[who].get("/api/tags")
        assert r.status_code == 200
        body = r.json()
        names = {t["name"] for t in body["tags"]}
        assert "confidential/operation-zebra" not in names
        assert body["count"] == len(body["tags"])

    def test_tag_tree_has_no_private_branch(self, env, who):
        r = env[who].get("/api/tags/tree")
        assert r.status_code == 200
        assert "confidential" not in {n["name"] for n in r.json()["tree"]}

    def test_qa_status_totals_exclude_the_private_kb(self, env, who):
        """total_entries counts only readable KBs -- the public one has 2."""
        r = env[who].get("/api/qa/status")
        assert r.status_code == 200
        assert r.json()["total_entries"] == 2

    def test_qa_validate_all_lists_only_readable_kbs(self, env, who):
        r = env[who].get("/api/qa/validate")
        assert r.status_code == 200
        assert {k["kb_name"] for k in r.json()["kbs"]} == {PUBLIC}


@pytest.mark.parametrize("who", ["peer", "anon"])
class TestEntryOnlyInPrivateKBAddressedWithoutKB:
    """An entry id that exists only in the private KB, with `kb` omitted
    or defaulted, must not resolve."""

    def test_blocks_without_kb_is_422_or_404_never_private_content(self, env, who):
        r = env[who].get("/api/entries/secret-note/blocks")
        assert r.status_code in (404, 422)
        assert not [m for m in PRIVATE_MARKERS if m in r.text]

    def test_versions_without_kb_is_422_or_404(self, env, who):
        r = env[who].get("/api/entries/secret-note/versions")
        assert r.status_code in (404, 422)
        assert not [m for m in PRIVATE_MARKERS if m in r.text]

    def test_qa_validate_entry_without_kb_is_422_or_404(self, env, who):
        r = env[who].get("/api/qa/validate/secret-note")
        assert r.status_code in (404, 422)
        assert not [m for m in PRIVATE_MARKERS if m in r.text]


@pytest.mark.parametrize("who", ["peer", "anon"])
class TestErrorBodiesDoNotEchoPrivateNames:
    def test_daily_404_is_the_nonexistent_kb_404(self, env, who):
        """The KB_NOT_FOUND body names the KB the caller asked for -- which
        is fine, they typed it -- but it must be the *same* body a
        nonexistent KB gives, so the two are indistinguishable."""
        private = env[who].get(f"/api/daily/2021-06-15?kb={PRIVATE}")
        missing = env[who].get(f"/api/daily/2021-06-15?kb={NONEXISTENT}")
        assert private.status_code == missing.status_code == 404
        assert (
            private.json()["detail"]["code"] == missing.json()["detail"]["code"] == "KB_NOT_FOUND"
        )
        # No private *content* -- only the KB name the caller supplied.
        leaked = [m for m in PRIVATE_MARKERS if m in private.text]
        assert not leaked, leaked

    def test_templates_404_is_indistinguishable(self, env, who):
        private = env[who].get(f"/api/kbs/{PRIVATE}/templates")
        missing = env[who].get(f"/api/kbs/{NONEXISTENT}/templates")
        assert private.status_code == missing.status_code == 404


class TestAIRoutesOnlySeeReadableKBs:
    """The four AI POST routes are write-tier, so a read-only peer is
    already refused; what must also hold is that retrieval never reaches
    a KB the caller cannot read. Asserted on the retrieval call's
    kb_names, not on model output."""

    def test_ai_routes_reject_a_peer_without_write(self, env):
        for path, payload in [
            ("/api/ai/summarize", {"entry_id": "secret-note", "kb_name": PRIVATE}),
            ("/api/ai/auto-tag", {"entry_id": "secret-note", "kb_name": PRIVATE}),
            ("/api/ai/suggest-links", {"entry_id": "secret-note", "kb_name": PRIVATE}),
            (
                "/api/ai/chat",
                {"messages": [{"role": "user", "content": "zebra"}], "kb": PRIVATE},
            ),
        ]:
            r = env["peer"].post(path, json=payload)
            assert r.status_code in (403, 404), f"{path}: {r.status_code} {r.text[:200]}"
            assert not [m for m in PRIVATE_MARKERS if m in r.text], path

    def test_admin_chat_retrieval_is_unscoped(self, env, monkeypatch):
        """A caller who can read everything keeps kb_names=None."""
        seen = {}

        from pyrite.services.search_service import SearchService

        original = SearchService.search

        def spy(self, *args, **kwargs):
            seen.setdefault("kb_names", kwargs.get("kb_names", "<not passed>"))
            return original(self, *args, **kwargs)

        monkeypatch.setattr(SearchService, "search", spy)
        env["admin"].post(
            "/api/ai/chat",
            json={"messages": [{"role": "user", "content": "zebra"}]},
        )
        assert seen.get("kb_names") is None


class TestWhoCanSee:
    def test_admin_sees_everything(self, env):
        assert _kb_names(env["admin"].get("/api/kbs")) == {PUBLIC, PRIVATE}
        assert _ids(env["admin"].get("/api/search?q=zebra")) == {
            "public-note",
            "public-event",
            "secret-note",
            "secret-two",
            "secret-event",
        }

    def test_anonymous_sees_only_public(self, env):
        assert _kb_names(env["anon"].get("/api/kbs")) == {PUBLIC}
        assert _ids(env["anon"].get("/api/search?q=zebra")) == {"public-note", "public-event"}

    def test_a_grant_makes_it_visible(self, env):
        auth = AuthService(env["db"], env["config"].settings.auth)
        users = {u["username"]: u for u in auth.list_users()}
        auth.grant_kb_permission(users["peer"]["id"], PRIVATE, "read", users["admin-user"]["id"])
        assert _kb_names(env["peer"].get("/api/kbs")) == {PUBLIC, PRIVATE}
        assert env["peer"].get(f"/api/entries/secret-note?kb={PRIVATE}").status_code == 200
        assert "secret-note" in _ids(env["peer"].get("/api/search?q=zebra"))


@pytest.mark.parametrize("route", KB_NAMED_ROUTES)
class TestScopingIsNotAWallForCallersWhoMayRead:
    """The other half of every criterion above: a caller who may read the
    KB must still get through. A check that 404s everyone would pass every
    leak test in this file and be worthless."""

    def test_a_global_admin_is_never_404ed_by_scoping(self, env, route):
        r = env["admin"].get(route.format(kb=PRIVATE))
        assert r.status_code != 404 or "KB_NOT_FOUND" not in r.text, (
            f"{route}: scoping 404'd a global admin -- {r.text[:200]}"
        )

    def test_a_granted_peer_is_never_404ed_by_scoping(self, env, route):
        auth = AuthService(env["db"], env["config"].settings.auth)
        users = {u["username"]: u for u in auth.list_users()}
        auth.grant_kb_permission(users["peer"]["id"], PRIVATE, "read", users["admin-user"]["id"])
        r = env["peer"].get(route.format(kb=PRIVATE))
        assert r.status_code != 404 or "KB_NOT_FOUND" not in r.text, (
            f"{route}: scoping 404'd a peer holding a read grant -- {r.text[:200]}"
        )


@pytest.mark.parametrize("route", KB_SPANNING_ROUTES)
def test_a_global_admin_still_spans_every_kb(env, route):
    """The KB-spanning routes pass kb_names=None for an unscoped caller,
    so an admin's view is unchanged by this work."""
    r = env["admin"].get(route)
    assert r.status_code == 200, f"{route}: {r.text[:200]}"


def test_admin_timeline_and_tags_still_include_the_private_kb(env):
    """The sharpest form of "nothing changes for a caller who reads
    everything": the private rows are still there for an admin."""
    timeline = env["admin"].get("/api/timeline")
    assert {e["id"] for e in timeline.json()["events"]} == {"public-event", "secret-event"}
    tags = env["admin"].get("/api/tags")
    assert "confidential/operation-zebra" in {t["name"] for t in tags.json()["tags"]}
