"""Golden (status, body) for every KB-bearing REST operation, across the ADR
§5 principal matrix and the {readable, private, missing} KB axis (ADR-0037
theme 0).

Regenerate: ``PYRITE_CHARACTERIZATION_REGENERATE=1 .venv/bin/pytest
tests/characterization/test_rest_matrix.py -n4``, then review the diff to
``tests/characterization/goldens/rest.json`` and commit it as its own
reviewed change. Never set in CI or the pre-push hook.

**What "every operation" means here.** `surfaces.kb_bearing_rest_operations`
narrows `tests/_surface_inventory.py`'s 144 REST operations to the 66 that a
read- or write-scoping dependency actually attaches to (instance
administration, `/auth/*`, and static/site routes serve no KB content and
have no per-KB principal matrix to characterize -- see that module's
docstring). `rest_calls.build_call` supplies one real HTTP call per route,
targeting a KB name; a route this harness cannot meaningfully drive without
new fixture machinery (a registered repo, a review row, ...) returns a
``{"skip": reason}`` marker instead of request kwargs, recorded as skipped
rather than silently wrong -- see the report for the full skip list.

**Principals x KB states.** Every one of `world.py`'s seven principals is
run against `READABLE`, `PRIVATE` and `MISSING` (21 cases per route); a
route's golden key is ``"{METHOD} {path} | {principal} | {kb_state}"``.
"""

from __future__ import annotations

import pytest

from tests.characterization.golden_io import assert_matches, load, regenerating, save
from tests.characterization.normalize import normalize, normalize_rest_body
from tests.characterization.rest_calls import build_call
from tests.characterization.surfaces import kb_bearing_rest_operations
from tests.characterization.world import MISSING, PRIVATE, READABLE

# Not @pytest.mark.core -- see test_global_access.py's comment: core is an
# exact, pinned smoke-set file list (tests/test_test_affected.py), and this
# suite is deliberately heavier than that set. test-affected's import walker
# still selects this file whenever a branch touches pyrite.server.api or a
# module it imports.

GOLDEN_NAME = "rest"
KB_STATES = (READABLE, PRIVATE, MISSING)


class TestRestPrincipalMatrix:
    """One test per principal keeps a failure's pytest id naming exactly
    who was refused (or let through) wrongly, without a 21x-per-route
    parametrize id blowing up -- each principal's test parametrizes over
    routes x KB state only."""

    @staticmethod
    def _run(world, principal_name, golden):
        principal = world.principals[principal_name]
        ops = kb_bearing_rest_operations(world.app)
        skipped = []
        for op in ops:
            for kb_state in KB_STATES:
                # Releases this world's DB's per-thread fallback SQLAlchemy
                # sessions before every call (see
                # `World.release_idle_connections`'s docstring) -- without
                # it, this many `TestClient` requests against the shared
                # `get_db` override exhausts the connection pool partway
                # through one principal's 66-route sweep, and the request
                # that finds it empty hangs forever rather than erroring
                # (confirmed with faulthandler while building this harness;
                # a sparser interval was not reliably enough headroom for a
                # write-tier principal's heavier per-request session use).
                world.release_idle_connections()
                key = f"{op.method} {op.path} | {principal_name} | {kb_state}"
                kwargs = build_call(
                    world, op.method, op.path, kb_state, call_key=f"{principal_name}-{kb_state}"
                )
                if "skip" in kwargs:
                    skipped.append((key, kwargs["skip"]))
                    continue
                url = kwargs.pop("url")
                try:
                    resp = world.client.request(
                        op.method,
                        url,
                        headers=principal.rest_headers or None,
                        cookies=principal.rest_cookies or None,
                        **kwargs,
                    )
                except Exception as exc:  # noqa: BLE001
                    # An unhandled server-side exception (TestClient's
                    # default re-raises it rather than turning it into a
                    # 500 body) -- a real production bug this call tripped
                    # over, not an authorization behaviour. Recorded as its
                    # own golden shape so the matrix does not abort and the
                    # bug is pinned rather than silently retried away; see
                    # the report for what this found and #<issue>.
                    actual = {"unhandled_exception": f"{type(exc).__name__}: {exc}"}
                    assert_matches(GOLDEN_NAME, key, actual, golden)
                    continue
                try:
                    body = resp.json()
                except ValueError:
                    body = resp.text
                # normalize_rest_body blanks this route's enumeration-
                # sensitive fields (a count/list over "everything in a KB",
                # not the one row an identity-based route names) before the
                # timestamp/id/path normalisation `normalize` does -- see its
                # docstring and REST_ENUMERATION_SENSITIVE_FIELDS in
                # normalize.py. `status` is untouched either way.
                normalised_body = normalize_rest_body(
                    op.method, op.path, body, tmpdir=str(world.tmpdir)
                )
                actual = {"status": resp.status_code, "body": normalised_body}
                assert_matches(GOLDEN_NAME, key, actual, golden)
        return skipped

    @pytest.mark.parametrize(
        "principal_name",
        [
            "anonymous",
            "read_key",
            "write_key",
            "admin_key",
            "global_user",
            "local_user",
            "granted_user",
        ],
    )
    def test_principal(self, world, principal_name):
        golden = load(GOLDEN_NAME)
        skipped = self._run(world, principal_name, golden)
        if regenerating():
            save(GOLDEN_NAME, golden)
        # Recorded via a module-level accumulator so the report's skip list
        # is the union across principals (a route's skip reason does not
        # depend on the principal), deduplicated by route.
        _SKIPPED.update(dict(skipped))


_SKIPPED: dict[str, str] = {}


def test_skip_list_is_reported(world):
    """Not a golden assertion: prints the skip list to the pytest report
    (`-s` or a failure) so a human reads it, per the theme's "list and skip
    with a reason" acceptance. Runs last (name sorts after test_principal's
    module, and pytest here runs classes before a trailing module-level
    def in source order) -- if this shows 0 the matrix test above did not
    run first; check test order.
    """
    ops = kb_bearing_rest_operations(world.app)
    reasons: dict[str, str] = {}
    for op in ops:
        for kb_state in KB_STATES:
            kwargs = build_call(world, op.method, op.path, kb_state)
            if "skip" in kwargs:
                reasons[f"{op.method} {op.path}"] = kwargs["skip"]
    print(f"\n{len(reasons)} REST route(s) skipped (not driven by this harness):")
    for route, reason in sorted(reasons.items()):
        print(f"  {route}: {reason}")
