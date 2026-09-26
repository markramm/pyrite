"""Golden result for every KB-bearing MCP tool, across the ADR §5 principal
matrix and the {readable, private, missing} KB axis (ADR-0037 theme 0).

Regenerate: ``PYRITE_CHARACTERIZATION_REGENERATE=1 .venv/bin/pytest
tests/characterization/test_mcp_matrix.py -n4``, then review the diff to
``tests/characterization/goldens/mcp.json`` and commit it as its own
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

**106 KB-bearing tools x 7 principals x 3 KB states** = 2226 dispatch calls.
`_dispatch_tool` is synchronous, in-process Python with no I/O beyond a
handler's own service calls -- cheap compared to REST's real HTTP round
trips, so all of it runs in one parametrized test rather than split by
principal.
"""

from __future__ import annotations

import pytest

from tests.characterization.golden_io import assert_matches, load, regenerating, save
from tests.characterization.mcp_calls import build_arguments
from tests.characterization.normalize import normalize_mcp_result
from tests.characterization.surfaces import kb_bearing_mcp_tool_names
from tests.characterization.world import MISSING, PRIVATE, READABLE

# Not @pytest.mark.core -- see test_global_access.py's comment on why: core
# is an exact, pinned smoke-set file list, and this suite is deliberately
# heavier than that set. test-affected's import walker still selects this
# file whenever a branch touches pyrite.server.mcp_server or a module it
# imports.

GOLDEN_NAME = "mcp"
KB_STATES = (READABLE, PRIVATE, MISSING)
PRINCIPAL_NAMES = (
    "anonymous",
    "read_key",
    "write_key",
    "admin_key",
    "global_user",
    "local_user",
    "granted_user",
)


@pytest.mark.parametrize("principal_name", PRINCIPAL_NAMES)
def test_mcp_tool_principal_matrix(world, principal_name):
    principal = world.principals[principal_name]
    golden = load(GOLDEN_NAME)
    tool_names = kb_bearing_mcp_tool_names(world.mcp_server)
    for tool_name in tool_names:
        for kb_state in KB_STATES:
            key = f"{tool_name} | {principal_name} | {kb_state}"
            # Deterministic across regenerate and compare runs (same
            # tool/principal/kb_state -> same call_key every time), and
            # unique per case, so a write tool run against the shared,
            # session-scoped world never collides with another case's
            # earlier write (see mcp_calls.py's `_UNIQUE_PER_CALL`).
            call_key = f"{tool_name}-{principal_name}-{kb_state}".replace("/", "_")
            arguments = build_arguments(world, tool_name, kb_state, call_key=call_key)
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
            assert_matches(GOLDEN_NAME, key, actual, golden)
    if regenerating():
        save(GOLDEN_NAME, golden)
