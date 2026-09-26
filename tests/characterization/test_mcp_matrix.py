"""Golden result for every KB-bearing MCP tool, across the ADR §5 principal
matrix and the {readable, private, missing, no_default_role} KB axis
(ADR-0037 theme 0).

Regenerate: ``PYRITE_CHARACTERIZATION_REGENERATE=1 .venv/bin/pytest
tests/characterization/test_mcp_matrix.py -n4``, then review the diff to
``tests/characterization/goldens/mcp.*.json`` and commit it as its own
reviewed change. Never set in CI or the pre-push hook.

**Calling through the real chokepoint, not the wire.** Every case calls
`world.mcp_server._dispatch_tool(name, arguments, client_id=..., readable_kbs=...,
writable_kbs=...)` directly -- the same function every transport (stdio,
SSE, the in-memory SDK session `test_mcp_read_scoping.py` drives) funnels
through, and the one place scoping and the write-tier rule are enforced
(`pyrite/server/mcp_server.py`'s own docstring on `_dispatch_tool`). Theme 0
pins that function's output; it does not additionally prove the SDK
transport wiring reaches it, which is a *different*, already-covered
question (`test_mcp_read_scoping.py`'s docstring explains why it drives a
real session instead).

**106 KB-bearing tools x 7 principals x 4 KB states** = 2968 dispatch calls.
`_dispatch_tool` is synchronous, in-process Python with no I/O beyond a
handler's own service calls -- cheap compared to REST's real HTTP round
trips, so all of it runs in one parametrized test rather than split by
principal.

**The run set is the golden, not a live filter (#476 blocker 1).** Same
problem, same fix as `test_rest_matrix.py`: a migration that renames what
`surfaces.py` matches (a KB-argument-shaped schema property, or the
`readable_kbs` opt-in keyword) makes `kb_bearing_mcp_tool_names` return
fewer tools -- silently. This file computes the UNION of `live` (today's
`kb_bearing_mcp_tool_names`) and `golden` (what's on disk for this
principal) and runs both; a tool only in `golden` dropped out of scoping
and must still be driven. `test_no_golden_mcp_tool_is_orphaned` and
`test_surface_counts_are_pinned` below are this file's own direct proof of
that, over the MCP surface (`test_rest_matrix.py` has the REST-side twins).
"""

from __future__ import annotations

import pytest

from tests.characterization.golden_io import MismatchCollector, load, regenerating, save
from tests.characterization.mcp_calls import build_arguments
from tests.characterization.normalize import normalize_mcp_result
from tests.characterization.surfaces import kb_bearing_mcp_tool_names
from tests.characterization.world import MISSING, NO_DEFAULT_ROLE, PRIVATE, READABLE

# Not @pytest.mark.core -- see test_global_access.py's comment on why: core
# is an exact, pinned smoke-set file list, and this suite is deliberately
# heavier than that set. test-affected's import walker still selects this
# file whenever a branch touches pyrite.server.mcp_server or a module it
# imports.

GOLDEN_NAME = "mcp"
KB_STATES = (READABLE, PRIVATE, MISSING, NO_DEFAULT_ROLE)
PRINCIPAL_NAMES = (
    "anonymous",
    "read_key",
    "write_key",
    "admin_key",
    "global_user",
    "local_user",
    "granted_user",
)


def _golden_tools_for(principal_name: str, golden: dict) -> set[str]:
    """Every distinct tool name this principal has a golden case for,
    parsed back out of the golden's own key format
    (``"{tool} | {principal} | {kb_state}"``)."""
    tools: set[str] = set()
    prefix_suffix = f" | {principal_name} | "
    for key in golden:
        if prefix_suffix not in key:
            continue
        tools.add(key.split(prefix_suffix)[0])
    return tools


@pytest.mark.parametrize("principal_name", PRINCIPAL_NAMES)
def test_mcp_tool_principal_matrix(world, principal_name):
    principal = world.principals[principal_name]
    golden = load(GOLDEN_NAME)
    collector = MismatchCollector()
    live_tools = set(kb_bearing_mcp_tool_names(world.mcp_server))
    golden_tools = _golden_tools_for(principal_name, golden)
    # The union: a tool only in `golden_tools` dropped out of live scoping
    # (a renamed KB-argument convention, say) and must still be driven --
    # see the module docstring, #476 blocker 1.
    all_tools = live_tools | golden_tools
    for tool_name in sorted(all_tools):
        for kb_state in KB_STATES:
            key = f"{tool_name} | {principal_name} | {kb_state}"
            # Deterministic across regenerate and compare runs (same
            # tool/principal/kb_state -> same call_key every time), and
            # unique per case, so a write tool run against the shared,
            # session-scoped world never collides with another case's
            # earlier write (see mcp_calls.py's `_UNIQUE_PER_CALL`).
            call_key = f"{tool_name}-{principal_name}-{kb_state}".replace("/", "_")
            try:
                arguments = build_arguments(world, tool_name, kb_state, call_key=call_key)
            except KeyError:
                # A golden-only tool `mcp_calls.py` no longer recognises at
                # all (the tool itself, not just its scoping, was removed).
                collector.check(GOLDEN_NAME, key, {"no_call_spec": True}, golden)
                continue
            result = world.mcp_server._dispatch_tool(
                tool_name,
                arguments,
                # A unique client_id per case: MCPRateLimiter is keyed by
                # client_id, and this matrix makes far more calls per
                # principal than the read-tier rate limit allows -- a
                # shared client_id would make later cases in the same
                # principal's run answer RATE_LIMITED (with a wall-clock
                # "retry after Ns" that is itself nondeterministic) instead
                # of their real authorization outcome, which is not what
                # this harness characterizes.
                client_id=f"characterization-{call_key}",
                readable_kbs=set(principal.readable_kbs)
                if principal.readable_kbs is not None
                else None,
                writable_kbs=set(principal.writable_kbs)
                if principal.writable_kbs is not None
                else None,
            )
            actual = normalize_mcp_result(tool_name, result, tmpdir=str(world.tmpdir))
            collector.check(GOLDEN_NAME, key, actual, golden)
    if regenerating():
        save(GOLDEN_NAME, golden, principal_scope=principal_name)
    collector.assert_clean()


PINNED_MCP_TOOL_COUNT = 106


def test_no_golden_mcp_tool_is_orphaned(world):
    """A tool in the golden but no longer in the LIVE surface fails here,
    by name (#476 blocker 1's MCP counterpart) -- the same proof as REST's
    `test_no_golden_key_is_orphaned`, for a renamed KB-argument convention
    or a removed `readable_kbs` opt-in instead of a renamed dependency.
    """
    golden = load(GOLDEN_NAME)
    live_tools = set(kb_bearing_mcp_tool_names(world.mcp_server))
    all_golden_tools: set[str] = set()
    for principal_name in PRINCIPAL_NAMES:
        all_golden_tools |= _golden_tools_for(principal_name, golden)
    orphaned = sorted(all_golden_tools - live_tools)
    assert not orphaned, (
        f"{len(orphaned)} tool(s) have a golden case but no longer appear in "
        f"kb_bearing_mcp_tool_names -- a KB-argument convention or the "
        f"readable_kbs opt-in likely changed, and this run set no longer covers "
        f"it: {orphaned}"
    )


def test_surface_counts_are_pinned(world):
    """The number of KB-bearing MCP tools, pinned (#476 blocker 1): a
    change -- growing OR shrinking -- means the surface filter's idea of
    "takes a KB or row resource" changed, and a reviewer should see that as
    a diff to this constant. REST's count (66... now more, see
    `test_rest_matrix.py`'s own `PINNED_REST_OPERATION_COUNT`) is pinned
    there, in the module that owns REST's surface.
    """
    live_tools = set(kb_bearing_mcp_tool_names(world.mcp_server))
    assert len(live_tools) == PINNED_MCP_TOOL_COUNT, (
        f"kb_bearing_mcp_tool_names now returns {len(live_tools)} distinct tools, "
        f"pinned at {PINNED_MCP_TOOL_COUNT} -- update PINNED_MCP_TOOL_COUNT "
        f"deliberately (with a reason for the change) rather than letting it drift."
    )
