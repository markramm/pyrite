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

import pytest

from tests.characterization.error_bodies import all_error_body_cases
from tests.characterization.golden_io import MismatchCollector, load, save, regenerating
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
    # A collector, not a bare assert (#476 blocker 7): a change to the
    # shared REST classification table or a shared MCP/CLI mapping function
    # can affect several PyriteError classes in one policy change, and the
    # report should show every class it moved, not just the
    # alphabetically-first one a bare assert would stop at.
    collector = MismatchCollector()
    for case in all_error_body_cases():
        key = case.class_name
        actual = {
            "rest": normalize(case.rest, tmpdir=str(world.tmpdir)),
            "mcp": normalize(case.mcp, tmpdir=str(world.tmpdir)),
            "cli": normalize(case.cli, tmpdir=str(world.tmpdir)),
        }
        collector.check(GOLDEN_NAME, key, actual, golden)
    if regenerating():
        save(GOLDEN_NAME, golden)
    collector.assert_clean()


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


@pytest.mark.xfail(
    strict=True,
    reason="#491: kb_index_sync silently flips a config KB's registry `source` to "
    "'user', so a config KB is no longer protected once it has been synced. Pins "
    "TODAY's real behaviour rather than routing around it by re-seeding source="
    "'config' first (#476 blocker 6). xfail(strict=True): this must always fail "
    "for as long as #491 stands -- an unexpected PASS means #491 was fixed (or "
    "this test regressed), and CI, not silent order-dependence, is what would "
    "say so.",
)
def test_kb_protected_live_over_rest(world):
    # Deterministically triggers #491's precondition ITSELF (rather than
    # depending on whether some earlier, unrelated test in the same worker
    # happened to sync READABLE first -- that was the actual bug in the
    # ORIGINAL version of this test: its outcome depended on execution
    # order, which is exactly the class of nondeterminism this harness
    # exists to eliminate elsewhere). A dedicated KB, synced once by this
    # test alone, makes the precondition -- and so the xfail -- a pure
    # function of this test, not of what ran before it.
    from pyrite.config import KBConfig

    kb_name = "characterization-491-repro"
    kb_path = world.tmpdir / kb_name
    kb_path.mkdir(exist_ok=True)
    # `add_kb`, not a raw `.append()` to `knowledge_bases`: `PyriteConfig`
    # caches `_kb_by_name` at construction, and `get_kb()` (which
    # `sync_incremental` calls to find this KB at all) reads only that
    # cache -- a bare append leaves the cache stale and `get_kb` returns
    # None, so `sync_incremental` silently skips the KB entirely (found
    # while writing this repro: the sync appeared to succeed but touched
    # nothing, and the bug never triggered). `add_kb` updates both.
    world.config.add_kb(
        KBConfig(name=kb_name, path=kb_path, kb_type="generic", default_role="read")
    )
    world.mcp_server.registry.seed_from_config()  # source="config" for kb_name, as at real startup

    p = world.principals["admin_key"]
    sync_result = world.mcp_server._dispatch_tool(
        "kb_index_sync",
        {"kb_name": kb_name},
        client_id="characterization-491-repro",
        readable_kbs=None,
        writable_kbs=None,
    )
    assert "error" not in sync_result, sync_result  # the sync itself must succeed

    resp = world.client.delete(f"/api/kbs/{kb_name}", headers=p.rest_headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PROTECTED"


def test_clipper_blocked_host_live_over_rest(world):
    p = world.principals["admin_key"]
    resp = world.client.post(
        "/api/clip", json={"url": "http://127.0.0.1/", "kb": READABLE}, headers=p.rest_headers
    )
    assert resp.status_code in (400, 403, 422)
    assert resp.json()["detail"]["code"] == "CLIPPER_BLOCKED_HOST"
