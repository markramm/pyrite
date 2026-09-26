"""KB-or-row-bearing REST operations and MCP tools, filtered from the one
shared inventory (`tests/_surface_inventory.py`, ADR-0037).

Theme 0's acceptance is "every REST operation and every MCP tool that takes
a KB or row resource" -- not every operation full stop (``/health``,
``/config/branding``, instance/user administration serve no KB content and
have no per-KB principal matrix to characterize). This module reuses the
exact signals the two existing structural ratchets already trust, rather
than re-deriving a third notion of "takes a KB":

- REST: a route's dependant tree contains one of the read-scoping
  dependencies `tests/test_read_scoping_is_structural.py` walks
  (`requires_kb_read()`, `get_readable_kbs`, `assert_kb_readable`) or one of
  the write-scoping guards `tests/test_kb_write_guard_is_structural.py`
  walks (`requires_kb_tier`'s named and row forms). A route with any of
  these reads or writes exactly the KB (or the row's KB) the dependency
  resolves -- which is what "takes a KB or row resource" means operationally.
- MCP: a tool's `inputSchema` declares one of `KB_ARGUMENT_NAMES`, or its
  handler opts into the cross-KB `readable_kbs` keyword
  (`PyriteMCPServer._handler_takes_readable_kbs`) -- the same test
  `tests/test_mcp_tool_registry_is_scoped.py` runs. `NON_KB_CONTENT_TOOLS`
  (job status, registry admin, a per-user score) is excluded explicitly,
  the same list `_dispatch_tool`'s fail-closed check already exempts.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from fastapi.routing import APIRoute

from pyrite.server.api import KB_PARAM_NAMES  # noqa: F401 -- re-exported for goldens' use
from pyrite.server.mcp_server import KB_ARGUMENT_NAMES, NON_KB_CONTENT_TOOLS, PyriteMCPServer

# Qualified names of every dependency that scopes a route to a KB or a row's
# KB -- the union of the two existing structural ratchets' own lists.
_READ_SCOPING = {
    "pyrite.server.api.requires_kb_read.<locals>._check",
    "pyrite.server.api.get_readable_kbs",
    "pyrite.server.api.assert_kb_readable",
}
_WRITE_SCOPING = {
    "pyrite.server.api.requires_kb_tier.<locals>._check_kb_tier",
    "pyrite.server.api.requires_kb_tier.<locals>._check_row_kb_tier",
}
KB_SCOPING_DEPENDENCIES = _READ_SCOPING | _WRITE_SCOPING


def _dependency_names(dependant) -> set[str]:
    names: set[str] = set()
    for dep in dependant.dependencies:
        call = dep.call
        module = getattr(call, "__module__", "?")
        qualname = getattr(call, "__qualname__", repr(call))
        names.add(f"{module}.{qualname}")
        names |= _dependency_names(dep)
    return names


@dataclass(frozen=True)
class RestCase:
    method: str
    path: str
    route: APIRoute


def kb_bearing_rest_operations(app) -> list[RestCase]:
    """Every (method, path, route) whose dependant tree scopes it to a KB
    or a row's KB. Walks the same routes `tests/_surface_inventory.py`
    enumerates."""
    from tests._surface_inventory import _walk_routes

    out = []
    for path, route in _walk_routes(app.routes):
        if not isinstance(route, APIRoute):
            continue
        if not (_dependency_names(route.dependant) & KB_SCOPING_DEPENDENCIES):
            continue
        for method in sorted(route.methods or ()):
            if method in ("HEAD", "OPTIONS"):
                continue
            out.append(RestCase(method, path, route))
    return out


def kb_bearing_mcp_tool_names(server: PyriteMCPServer) -> list[str]:
    """Every tool name that names a KB argument or opts into the cross-KB
    `readable_kbs` keyword, excluding `NON_KB_CONTENT_TOOLS`."""
    out = []
    for name, meta in server.tools.items():
        if name in NON_KB_CONTENT_TOOLS:
            continue
        schema = meta.get("inputSchema") or {}
        props = set((schema.get("properties") or {}).keys())
        if (props & set(KB_ARGUMENT_NAMES)) or server._handler_takes_readable_kbs(name):
            out.append(name)
    return sorted(out)


def handler_signature_params(handler) -> set[str]:
    """Parameter names of a tool handler, for tests that need to know
    whether a handler takes `readable_kbs`/`writable_kbs`."""
    try:
        return set(inspect.signature(handler).parameters)
    except (TypeError, ValueError):  # pragma: no cover - exotic callables
        return set()
