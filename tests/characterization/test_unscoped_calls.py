"""Golden cases for the UNSCOPED (cross-KB, no ``kb``/``kb_name`` named)
call shape (#476 blocker 3).

The main matrix (`test_rest_matrix.py`, `test_mcp_matrix.py`) always names
one target KB per case, because that is what the ADR §5 principal x
KB-state matrix is: "can this principal read/write THIS KB". But a whole
class of routes and tools -- search, and every cross-KB listing -- has a
SECOND mode, reached only when the caller omits the KB name entirely: the
service is handed the caller's `readable_kbs` set (or `None`, unscoped, for
an operator key/global admin) instead. Cold review (#476) found this mode
was never exercised at all: every REST and MCP call spec always passed
`kb`/`kb_name`, so a regression like ``kb_names=None`` in
`endpoints/search.py` -- which unconditionally search-everywhere for EVERY
caller, scoped or not -- left every existing test green.

**This module drives that second mode directly**, for a representative
pair of routes/tools per surface (`GET /api/search`/`GET /api/entries` for
REST, `kb_search`/`kb_list_entries` for MCP -- the ones blocker 3 names by
example) across every principal, so a scoping regression on the unscoped
path is caught the same way the main matrix catches it on the named-KB
path. Not folded into the main matrix's KB-state axis, because "no KB
named" is not a KB state (readable/private/missing) -- it is a different
CALL SHAPE with its own golden key format,
``"{route/tool} UNSCOPED | {principal}"``.

Regenerate: ``PYRITE_CHARACTERIZATION_REGENERATE=1 .venv/bin/pytest
tests/characterization/test_unscoped_calls.py -n4``, then review the diff to
``tests/characterization/goldens/unscoped.json``. Never set in CI or the
pre-push hook.
"""

from __future__ import annotations

from tests.characterization.golden_io import MismatchCollector, load, regenerating, save
from tests.characterization.normalize import normalize_mcp_result, normalize_rest_body

GOLDEN_NAME = "unscoped"

PRINCIPAL_NAMES = (
    "anonymous",
    "read_key",
    "write_key",
    "admin_key",
    "global_user",
    "local_user",
    "granted_user",
)


def test_unscoped_rest_search_and_entries(world):
    golden = load(GOLDEN_NAME)
    collector = MismatchCollector()
    for principal_name in PRINCIPAL_NAMES:
        principal = world.principals[principal_name]
        for method, path, params in (
            ("GET", "/api/search", {"q": "zebra", "limit": 100}),  # route's cap (le=100)
            # A high limit: the shared world accumulates rows in READABLE/
            # PRIVATE/NO_DEFAULT_ROLE from every write-tool case across the
            # whole matrix (world.py's own perf tradeoff), so a low default
            # page size can push READ_ONLY's one fixed entry (or another
            # sparse KB) off the first page depending on how much noise
            # already piled up elsewhere -- not a scoping question, just
            # pagination interacting with accumulated content. A high limit
            # keeps every KB represented regardless of that noise; which KBs
            # appear at all (normalize.py's identity projection) is what
            # this test characterizes, not how many rows are in each.
            ("GET", "/api/entries", {"limit": 200}),
        ):
            key = f"{method} {path} UNSCOPED | {principal_name}"
            resp = world.client.request(
                method,
                path,
                params=params,
                headers=principal.rest_headers or None,
                cookies=principal.rest_cookies or None,
            )
            try:
                body = resp.json()
            except ValueError:
                body = resp.text
            normalised_body = normalize_rest_body(
                method, path, body, tmpdir=str(world.tmpdir), unscoped=True
            )
            actual = {"status": resp.status_code, "body": normalised_body}
            collector.check(GOLDEN_NAME, key, actual, golden)
    if regenerating():
        save(GOLDEN_NAME, golden)
    collector.assert_clean()


def test_unscoped_mcp_search_and_list_entries(world):
    golden = load(GOLDEN_NAME)
    collector = MismatchCollector()
    for principal_name in PRINCIPAL_NAMES:
        principal = world.principals[principal_name]
        for tool_name, arguments in (
            ("kb_search", {"query": "zebra", "limit": 200}),
            # A high limit -- see the REST test's identical comment: keeps
            # every KB represented in the results regardless of how much
            # accumulated noise other matrix cases already added elsewhere.
            ("kb_list_entries", {"limit": 200}),
        ):
            key = f"{tool_name} UNSCOPED | {principal_name}"
            result = world.mcp_server._dispatch_tool(
                tool_name,
                dict(arguments),
                client_id=f"unscoped-{tool_name}-{principal_name}",
                readable_kbs=set(principal.readable_kbs)
                if principal.readable_kbs is not None
                else None,
                writable_kbs=set(principal.writable_kbs)
                if principal.writable_kbs is not None
                else None,
            )
            actual = normalize_mcp_result(
                tool_name, result, tmpdir=str(world.tmpdir), unscoped=True
            )
            collector.check(GOLDEN_NAME, key, actual, golden)
    if regenerating():
        save(GOLDEN_NAME, golden)
    collector.assert_clean()
