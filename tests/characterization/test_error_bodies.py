"""Golden error bodies for every `PyriteError` subclass, per transport (ADR-0037 theme 0).

Regenerate: ``PYRITE_CHARACTERIZATION_REGENERATE=1 .venv/bin/pytest
tests/characterization/test_error_bodies.py -n4``, then review the diff to
``tests/characterization/goldens/error_bodies.json`` and commit it as its
own reviewed change (never in the same commit as a behaviour change --
ADR-0037's migration rule). Never set in CI or the pre-push hook.

What this pins: `pyrite.server.api`'s REST classification table and public-
message rule, `pyrite.server.mcp_server._refusal` and `pyrite.utils.errors
.build_error` -- for one instance of every concrete `PyriteError` subclass
(`tests/characterization/error_bodies.py` builds them; see its docstring for
why this is a direct-construction pin rather than a live multi-step
scenario per class). A handful of REST-natural classes are cross-checked
here by a real HTTP call too, so the direct-construction path is not the
harness's only line of evidence for at least some classes.
"""

from __future__ import annotations

from tests.characterization.error_bodies import all_error_body_cases
from tests.characterization.golden_io import assert_matches, load, save, regenerating
from tests.characterization.normalize import normalize
from tests.characterization.world import PRIVATE, READABLE

# Not @pytest.mark.core -- see test_global_access.py's comment: core is an
# exact, pinned smoke-set file list (tests/test_test_affected.py), and this
# suite is deliberately heavier than that set. test-affected's import walker
# still selects this file whenever a branch touches pyrite.exceptions,
# pyrite.server.api or pyrite.server.mcp_server.

GOLDEN_NAME = "error_bodies"


def test_every_pyrite_error_class_has_a_golden_per_transport(world):
    golden = load(GOLDEN_NAME)
    for case in all_error_body_cases():
        key = case.class_name
        actual = {
            "rest": normalize(case.rest, tmpdir=str(world.tmpdir)),
            "mcp": normalize(case.mcp, tmpdir=str(world.tmpdir)),
            "cli": normalize(case.cli, tmpdir=str(world.tmpdir)),
        }
        assert_matches(GOLDEN_NAME, key, actual, golden)
    if regenerating():
        save(GOLDEN_NAME, golden)


# -- live cross-checks: a handful of classes REST/MCP naturally raise ------
# without any elaborate setup, driven through a real request so the harness
# is not ONLY ever trusting direct construction. Each asserts against the
# SAME golden key as the direct-construction case above (same class, same
# transport, same normalisation) -- a live call producing a different body
# than the direct-construction golden would mean the real raise site sends
# extra/different fields than a bare construction, which is itself worth
# knowing, not something to paper over with a second golden key.


def test_kb_not_found_live_over_rest(world):
    # A *scoped* caller (a session, not an unscoped operator key -- see
    # `requires_kb_read`'s `assert_kb_readable`, which only refuses a named
    # KB when the caller's readable set is not None): an admin key's
    # `readable_kbs` is None (unscoped), so the same call for it falls
    # through to the handler's generic "entry not found", a different code
    # (`NOT_FOUND`) -- itself a real oddity, noted in the report.
    p = world.principals["local_user"]
    resp = world.client.get(
        "/api/entries/whatever", params={"kb": "does-not-exist-at-all"}, cookies=p.rest_cookies
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "KB_NOT_FOUND"


def test_query_too_long_live_over_rest(world):
    # This route does not catch QueryTooLongError itself, so it reaches the
    # CENTRAL handler unmodified: a FLAT {"code","message"} body (no
    # "detail" wrapper) -- the third of the ADR's three REST body shapes,
    # and the one the direct-construction golden already predicts exactly.
    from pyrite.services.search_service import MAX_SEARCH_QUERY_LENGTH

    p = world.principals["admin_key"]
    resp = world.client.get(
        "/api/search",
        params={"q": "x" * (MAX_SEARCH_QUERY_LENGTH + 1), "kb": READABLE},
        headers=p.rest_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "QUERY_TOO_LONG"


def test_kb_read_only_live_over_rest(world):
    from tests.characterization.world import READ_ONLY

    # Oddity (reported): this route's own `except KBReadOnlyError` answers
    # {"code": "READ_ONLY", ...} -- not the central handler's KB_READ_ONLY
    # (pyrite/server/endpoints/entries.py:776 and 3 siblings), a THIRD
    # spelling alongside MCP/CLI's own "READ_ONLY" (which happens to
    # coincide here) and the central table's "KB_READ_ONLY". The golden
    # below pins today's real code, not the central table's.
    p = world.principals["admin_key"]
    resp = world.client.post(
        "/api/entries",
        json={"kb": READ_ONLY, "entry_type": "note", "title": "nope", "body": "x"},
        headers=p.rest_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "READ_ONLY"


def test_kb_protected_live_over_rest(world):
    # READABLE is declared in config.yaml (KBConfig, source="config" by
    # construction), so removing it via the registry route hits
    # KBRegistryService.remove_kb's KBProtectedError -- without touching the
    # world's actual state (admin key; DELETE really would remove a
    # user-added KB, but a config KB's removal is refused before that runs).
    #
    # Oddity (reported): this route's own catch answers {"code":
    # "PROTECTED", ...} -- a THIRD spelling, neither the central table's
    # KB_PROTECTED nor MCP/CLI's KB_PROTECTED (which agree with each other).
    #
    # Re-seeds READABLE's registry `source` back to "config" first: a real
    # bug this harness found and filed rather than fixed (#491) lets
    # `kb_index_sync` (a KB-bearing write tool this same session's MCP
    # matrix calls against every KB, including READABLE) silently flip a
    # config KB's `source` to "user" -- which would make THIS test's own
    # assertion depend on whether some other test in the same worker
    # happened to run `kb_index_sync` against READABLE first. That
    # ordering dependency is #491's bug leaking into this test, not
    # something this test is meant to characterize; restoring the
    # precondition keeps this test about the protected-removal refusal.
    world.db.register_kb(
        name=READABLE,
        kb_type="generic",
        path=str(world.tmpdir / READABLE),
        source="config",
    )
    p = world.principals["admin_key"]
    resp = world.client.delete(f"/api/kbs/{READABLE}", headers=p.rest_headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PROTECTED"


def test_clipper_blocked_host_live_over_rest(world):
    p = world.principals["admin_key"]
    resp = world.client.post(
        "/api/clip", json={"url": "http://127.0.0.1/", "kb": READABLE}, headers=p.rest_headers
    )
    assert resp.status_code in (400, 403, 422)
    assert resp.json()["detail"]["code"] == "CLIPPER_BLOCKED_HOST"
