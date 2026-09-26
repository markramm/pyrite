"""KB-or-row-bearing REST operations and MCP tools, filtered from the one
shared inventory (`tests/_surface_inventory.py`, ADR-0037).

Theme 0's acceptance is "every REST operation and every MCP tool that takes
a KB or row resource". Two structurally-detected shapes cover most of it,
reusing the exact signals the two existing structural ratchets already trust
(so this module never re-derives a third notion of "takes a KB"):

- REST: a route's dependant tree contains one of the read-scoping
  dependencies `tests/test_read_scoping_is_structural.py` walks
  (`requires_kb_read()`, `get_readable_kbs`, `assert_kb_readable`) or one of
  the write-scoping guards `tests/test_kb_write_guard_is_structural.py`
  walks (`requires_kb_tier`'s named and row forms).
- MCP: a tool's `inputSchema` declares one of `KB_ARGUMENT_NAMES`, or its
  handler opts into the cross-KB `readable_kbs` keyword
  (`PyriteMCPServer._handler_takes_readable_kbs`) -- the same test
  `tests/test_mcp_tool_registry_is_scoped.py` runs.

**A third shape exists, and it is not structurally detectable: a route or
tool that decides per-KB access INLINE**, reading `request.state.auth_user`/
`api_role` directly and calling `AuthService.get_kb_role`/
`resolve_kb_default_role` itself rather than through one of the two
dependency shapes above. `surfaces.py` used to call this whole remainder
"instance administration... [with] no per-KB principal matrix to
characterize" -- wrong for exactly this shape, and cold review (#476 blocker
4) caught it: `GET`/`POST /api/kbs/{name}/permissions` decide admin-or-KB-
admin access for a NAMED KB inline (`pyrite/server/endpoints/admin.py`'s
`list_kb_permissions`/`manage_kb_permission`), invisible to both dependency
walks, and were silently uncharacterized. `INLINE_ACCESS_DECIDING_ROUTES`
below is the explicit, hand-maintained, individually-verified list of these
-- unioned into `kb_bearing_rest_operations`'s output -- because there is no
dependency shape to detect them by; each entry names why it belongs there,
the same discipline `ALLOWLIST` uses for the opposite case.

**What's left out is `REST_ACCESS_EXCLUSIONS`/`MCP_ACCESS_EXCLUSIONS`: an
explicit, counted, per-route reason, never a blanket label.** Every
excluded route/tool was read, not assumed: `PUT`/`DELETE /api/kbs/{name}`,
reindex, `default-role`, `publish`/`commit`/`push`, and the MCP
`kb_registry_*` family all gate on `requires_tier("admin")` (REST) or the
admin TOOL tier (MCP) alone -- instance-wide, with no per-KB branch in the
handler, unlike `permissions` above -- so a `{readable, private, missing}`
axis has nothing to vary over (`private` and `readable` answer identically
for a global admin, and a migration to per-KB policy has no home to move
this check TO, because it is not one). `/api/settings*` and `/auth/users*`
name no KB at all (a settings key, a user id). `/api/admin/merge-queue*`
gates on `requires_tier("admin")` alone by design (an admin reviews every
KB's pending worktrees, private or not) -- the `kb=` query filter narrows
the listing, it does not gate it. `/site/*` and `/api/index/sync` are
already-documented public/instance-wide surfaces (`/site/*` serves a
static, pre-rendered cache with no auth dependency at all, the same
"anonymous, always-public" class ADR-0037 §5 names for SEO/branding
routes -- confirmed by reading `pyrite/server/static.py`).
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

# Routes that decide per-KB access INLINE (no dependency shape catches
# them): read, verified against `pyrite/server/endpoints/admin.py`
# (#476 blocker 4). Both call `auth_service.get_kb_role(auth_user["id"],
# name, kb_default_role)` for the NAMED KB when the caller is not a global
# admin -- a real per-KB decision, so both get a real golden case.
INLINE_ACCESS_DECIDING_ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/api/kbs/{name}/permissions"): (
        "list_kb_permissions calls AuthService.get_kb_role(user, name, "
        "default_role) inline when the caller is not a global admin -- a "
        "per-KB admin-or-not decision no FastAPI dependency expresses."
    ),
    ("POST", "/api/kbs/{name}/permissions"): (
        "manage_kb_permission (grant/revoke) makes the identical inline "
        "per-KB decision before granting or revoking a permission on the "
        "named KB."
    ),
}

# Routes with NO per-KB component at all: read and verified individually,
# never a blanket "administration" label (#476 blocker 4's own complaint).
# Pinned count so growing this list is a reviewed, visible diff, not a
# silent one -- see `test_rest_matrix.py::test_surface_counts_are_pinned`.
REST_ACCESS_EXCLUSIONS: dict[tuple[str, str], str] = {
    ("PUT", "/api/kbs/{name}"): "requires_tier('admin') only; update_kb has no per-KB branch.",
    ("DELETE", "/api/kbs/{name}"): (
        "requires_tier('admin') only; remove_kb's only per-KB fact is "
        "source=='config' (KBProtectedError), not the caller's role on it."
    ),
    ("POST", "/api/kbs/{name}/reindex"): "requires_tier('admin') only; no per-KB branch.",
    ("PUT", "/api/kbs/{name}/default-role"): "requires_tier('admin') only; no per-KB branch.",
    ("POST", "/api/kbs/{kb_name}/publish"): "requires_tier('admin') only; no per-KB branch.",
    ("POST", "/api/kbs/{kb_name}/commit"): "requires_tier('admin') only; no per-KB branch.",
    ("POST", "/api/kbs/{kb_name}/push"): "requires_tier('admin') only; no per-KB branch.",
    ("POST", "/api/index/sync"): "requires_tier('admin') only; syncs every KB, not one.",
    ("GET", "/api/settings"): "names no KB at all -- instance-wide configuration.",
    ("PUT", "/api/settings"): "names no KB at all -- instance-wide configuration.",
    ("GET", "/api/settings/{key}"): "names a settings key, not a KB.",
    ("PUT", "/api/settings/{key}"): "names a settings key, not a KB.",
    ("DELETE", "/api/settings/{key}"): "names a settings key, not a KB.",
    ("GET", "/auth/users"): "names no KB at all -- instance-wide user list, _ADMIN_ONLY.",
    ("PUT", "/auth/users/{user_id}/role"): "names a user id, not a KB; _ADMIN_ONLY.",
    ("GET", "/auth/users/{user_id}/permissions"): (
        "names a user id, not a KB; the response lists that user's per-KB "
        "grants, but the ACCESS GATE is _ADMIN_ONLY regardless of which "
        "KBs appear in the answer."
    ),
    ("GET", "/api/admin/merge-queue"): (
        "requires_tier('admin') only, by design -- an admin reviews every "
        "KB's pending worktrees; the optional kb= query narrows the "
        "listing, it does not gate it."
    ),
    (
        "GET",
        "/api/admin/merge-queue/{username}/diff",
    ): "requires_tier('admin') only, same as above.",
    (
        "POST",
        "/api/admin/merge-queue/{username}/merge",
    ): "requires_tier('admin') only, same as above.",
    (
        "POST",
        "/api/admin/merge-queue/{username}/reject",
    ): "requires_tier('admin') only, same as above.",
    (
        "GET",
        "/site",
    ): "static, pre-rendered cache; no auth dependency at all (anonymous, always-public).",
    ("GET", "/site/{path:path}"): "static, pre-rendered cache; no auth dependency at all.",
    ("GET", "/site/search"): "static, pre-rendered cache; no auth dependency at all.",
    ("GET", "/site/sitemap.xml"): "static, pre-rendered cache; no auth dependency at all.",
    ("GET", "/site/robots.txt"): "static, pre-rendered cache; no auth dependency at all.",
    ("GET", "/site/_static/{name}"): "static asset serving; no auth dependency at all.",
}
REST_ACCESS_EXCLUSIONS_COUNT = len(REST_ACCESS_EXCLUSIONS)

# The MCP kb_registry_* family: admin TOOL tier only (ADMIN_TOOLS in
# tool_schemas.py), the same "instance-wide, no per-KB branch" shape as
# their REST admin.py counterparts above -- read and verified individually
# in pyrite/server/mcp_server.py.
MCP_ACCESS_EXCLUSIONS: dict[str, str] = {
    "kb_registry_add": "admin tool tier only; registers a NEW KB, so there is no existing KB to vary over.",
    "kb_registry_remove": (
        "admin tool tier only; remove_kb's only per-KB fact is "
        "source=='config' (KBProtectedError), not the caller's role."
    ),
    "kb_registry_reindex": "admin tool tier only; no per-KB branch beyond KBNotFoundError.",
    "kb_registry_health": "admin tool tier only; no per-KB branch beyond KBNotFoundError.",
}
MCP_ACCESS_EXCLUSIONS_COUNT = len(MCP_ACCESS_EXCLUSIONS)


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
    or a row's KB, UNIONED with `INLINE_ACCESS_DECIDING_ROUTES` (no
    dependency shape catches those). Walks the same routes
    `tests/_surface_inventory.py` enumerates."""
    from tests._surface_inventory import _walk_routes

    out = []
    for path, route in _walk_routes(app.routes):
        if not isinstance(route, APIRoute):
            continue
        scoped = bool(_dependency_names(route.dependant) & KB_SCOPING_DEPENDENCIES)
        for method in sorted(route.methods or ()):
            if method in ("HEAD", "OPTIONS"):
                continue
            if scoped or (method, path) in INLINE_ACCESS_DECIDING_ROUTES:
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
