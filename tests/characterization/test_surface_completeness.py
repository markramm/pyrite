"""Every route in `create_app()` and every MCP tool is either characterized
or excluded with a reason (ADR-0037 theme 0, #476 round-2 issue 2).

Before this file existed, `surfaces.py`'s own module docstring CLAIMED "68
characterized, 26 excluded with a reason" as if that were an enforced
total, but nothing checked it against the live route table -- a full sweep
against `create_app()` found 49 routes (out of 143) in neither set, six of
them named explicitly in the round-2 cold read. This file is that missing
enforcement: `test_every_rest_route_is_covered` and
`test_every_mcp_tool_is_covered` fail, by name, on any route/tool that is
neither in `kb_bearing_rest_operations`/`kb_bearing_mcp_tool_names` NOR in
`REST_ACCESS_EXCLUSIONS`/`MCP_ACCESS_EXCLUSIONS` -- so a newly added route
that decides access (or plainly doesn't) can never merge silently
uncovered again. `test_exclusion_counts_are_pinned` pins the exclusion
COUNTS themselves (not just the coverage), the same discipline
`test_surface_counts_are_pinned` already applies to the characterized
counts in `test_rest_matrix.py`/`test_mcp_matrix.py` -- a change, growing
or shrinking, is a reviewed diff to a constant, never a silent drift.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from tests._surface_inventory import _walk_routes
from tests.characterization.surfaces import (
    MCP_ACCESS_EXCLUSIONS,
    MCP_ACCESS_EXCLUSIONS_COUNT,
    REST_ACCESS_EXCLUSIONS,
    REST_ACCESS_EXCLUSIONS_COUNT,
    kb_bearing_mcp_tool_names,
    kb_bearing_rest_operations,
)

PINNED_REST_TOTAL_ROUTE_COUNT = 143
PINNED_MCP_TOTAL_TOOL_COUNT = 112


def _all_rest_routes(app) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for path, route in _walk_routes(app.routes):
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or ()):
            if method in ("HEAD", "OPTIONS"):
                continue
            out.add((method, path))
    return out


def test_every_rest_route_is_covered(world):
    """A route neither characterized nor excluded is a route nobody has
    decided anything about -- fails here, by name, rather than silently
    shipping unreviewed (#476 round-2 issue 2)."""
    all_routes = _all_rest_routes(world.app)
    characterized = {(op.method, op.path) for op in kb_bearing_rest_operations(world.app)}
    excluded = set(REST_ACCESS_EXCLUSIONS.keys())
    uncovered = sorted(all_routes - characterized - excluded)
    assert not uncovered, (
        f"{len(uncovered)} REST route(s) are neither characterized "
        f"(kb_bearing_rest_operations) nor excluded (REST_ACCESS_EXCLUSIONS) -- "
        f"add each to one or the other, with a reason: {uncovered}"
    )


def test_every_mcp_tool_is_covered(world):
    """The MCP twin of `test_every_rest_route_is_covered`."""
    all_tools = set(world.mcp_server.tools.keys())
    characterized = set(kb_bearing_mcp_tool_names(world.mcp_server))
    excluded = set(MCP_ACCESS_EXCLUSIONS.keys())
    uncovered = sorted(all_tools - characterized - excluded)
    assert not uncovered, (
        f"{len(uncovered)} MCP tool(s) are neither characterized "
        f"(kb_bearing_mcp_tool_names) nor excluded (MCP_ACCESS_EXCLUSIONS) -- "
        f"add each to one or the other, with a reason: {uncovered}"
    )


def test_exclusion_counts_are_pinned():
    """`surfaces.py`'s module docstring used to CLAIM a count with nothing
    behind it (#476 round-2 issue 2's "the comment claims one that doesn't
    exist"). These are the real, enforced totals: a change -- growing OR
    shrinking -- means a route/tool moved between characterized and
    excluded, or a new one arrived, and a reviewer should see that as a
    diff to a constant, not discover it by reading a diff to a dict.
    """
    assert REST_ACCESS_EXCLUSIONS_COUNT == len(REST_ACCESS_EXCLUSIONS) == 69, (
        f"REST_ACCESS_EXCLUSIONS now has {len(REST_ACCESS_EXCLUSIONS)} entries, "
        f"pinned at 69 -- update this assert deliberately, with a reason, rather "
        f"than letting it drift."
    )
    assert MCP_ACCESS_EXCLUSIONS_COUNT == len(MCP_ACCESS_EXCLUSIONS) == 6, (
        f"MCP_ACCESS_EXCLUSIONS now has {len(MCP_ACCESS_EXCLUSIONS)} entries, "
        f"pinned at 6 -- update this assert deliberately, with a reason, rather "
        f"than letting it drift."
    )


def test_rest_total_route_count_is_pinned(world):
    """The size of the surface itself, pinned: a route added or removed
    from `create_app()` entirely (not just recategorized) is exactly the
    kind of change `test_every_rest_route_is_covered` cannot catch on its
    own -- a NEW route with no coverage at all still fails that test, but
    a route REMOVED from the app while its exclusion/characterization
    entry is left behind would not shrink `uncovered`, and nothing else
    here would notice. This constant is the tripwire for that case.
    """
    total = len(_all_rest_routes(world.app))
    assert total == PINNED_REST_TOTAL_ROUTE_COUNT, (
        f"create_app() now has {total} distinct (method, path) routes, pinned at "
        f"{PINNED_REST_TOTAL_ROUTE_COUNT} -- a route was added or removed; update "
        f"this constant AND surfaces.py's characterized/excluded sets together."
    )


def test_mcp_total_tool_count_is_pinned(world):
    """The MCP twin of `test_rest_total_route_count_is_pinned`."""
    total = len(world.mcp_server.tools)
    assert total == PINNED_MCP_TOTAL_TOOL_COUNT, (
        f"the admin-tier MCP server now registers {total} tools, pinned at "
        f"{PINNED_MCP_TOTAL_TOOL_COUNT} -- a tool was added or removed; update "
        f"this constant AND surfaces.py's characterized/excluded sets together."
    )
