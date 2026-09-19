"""Every /api route is scoped to the KBs its caller may read -- structurally.

Per-KB read scoping (`requires_kb_read`, `get_readable_kbs` in
`pyrite/server/api.py`) is what keeps a private KB invisible to a caller
without a grant. Nothing enforced that a *new* route picked it up, so
sixteen endpoint modules shipped without it and the rule lived only in a
docstring. This test is the enforcement: it walks the real app's routes
and fails for any `/api` route that is neither scoped nor explicitly
allowlisted with a reason.

**How scoping is detected: the dependency tree, not the handler body.**
Every route's `route.dependant` is walked recursively and each
dependency's callable is matched by qualified name against
`SCOPING_DEPENDENCIES`. Reading the handler's source instead (grep for
`readable_kbs` in the function body) was rejected: it cannot see scoping
that lives in a helper the handler calls, it happily matches a comment or
a variable of the same name, and it gives no way to be sure the check
actually runs on every request. A FastAPI dependency does run on every
request, and the dependant tree is the framework's own record of that.
The cost is a real constraint on authors: **scope a route by declaring
`Depends(requires_kb_read())` or taking `Depends(get_readable_kbs)`**,
never by calling `readable_kbs()` ad hoc inside the handler. Both forms
appear in the tree; a bare call does not, and this test will fail --
correctly, because such a call is invisible to review.
"""

from fastapi.routing import APIRoute

from pyrite.server.api import create_app

# Qualified names of the dependencies that scope a route's reads. A route
# whose dependant tree contains any of these is scoped:
#   - requires_kb_read()  -- 404s a named KB the caller may not read
#   - get_readable_kbs    -- hands the handler the readable set to filter by
#   - assert_kb_readable  -- the underlying assertion, if wired as a dependency
SCOPING_DEPENDENCIES = {
    "pyrite.server.api.requires_kb_read.<locals>._check",
    "pyrite.server.api.get_readable_kbs",
    "pyrite.server.api.assert_kb_readable",
}

# Routes that serve no KB content, or whose scoping is part 2 of this work.
# EVERY entry carries a reason. A route that leaks KB content does not
# belong here -- scope it instead.
ALLOWLIST: dict[tuple[str, str], str] = {
    # -- serves no KB content -------------------------------------------
    (
        "GET",
        "/api/collections/types",
    ): "serves no KB content: static + plugin collection type descriptors",
    (
        "GET",
        "/api/entries/types",
    ): "serves no KB content: distinct entry-type names, scoped in part 2 with the type-schema routes",
    (
        "GET",
        "/api/entries/type-schemas",
    ): "serves no KB content: plugin-declared type schemas, not KB rows",
    # -- write routes: guarded by requires_kb_tier('write')/requires_tier -
    # A write-tier caller on a KB can necessarily read it, so the write
    # guard subsumes the read guard. Listed rather than silently skipped
    # so that a write route losing its guard is still visible here.
    ("POST", "/api/entries"): "write route: requires_kb_tier('write') subsumes read",
    ("PUT", "/api/entries/{entry_id}"): "write route: requires_kb_tier('write') subsumes read",
    ("PATCH", "/api/entries/{entry_id}"): "write route: requires_kb_tier('write') subsumes read",
    ("DELETE", "/api/entries/{entry_id}"): "write route: requires_kb_tier('write') subsumes read",
    ("POST", "/api/entries/import"): "write route: requires_kb_tier('write') subsumes read",
    ("POST", "/api/clip"): "write route: requires_kb_tier('write') subsumes read",
    ("POST", "/api/collections"): "write route: requires_kb_tier('write') subsumes read",
    ("POST", "/api/daily/{date_str}"): "write route: requires_kb_tier('write') subsumes read",
    ("POST", "/api/starred"): "write route: requires_tier('write') subsumes read",
    ("PUT", "/api/starred/reorder"): "write route: requires_tier('write') subsumes read",
    ("DELETE", "/api/starred/{entry_id}"): "write route: requires_tier('write') subsumes read",
    ("POST", "/api/tasks/{task_id}/claim"): "write route: requires_kb_tier('write') subsumes read",
    ("POST", "/api/reviews"): "write route: requires_kb_tier('write') subsumes read",
    ("DELETE", "/api/reviews/{review_id}"): "write route: requires_kb_tier('write') subsumes read",
    # -- part 2: meta/admin surfaces ------------------------------------
    ("GET", "/api/stats"): "part 2: admin.py -- index-wide counts, no per-KB scoping today",
    ("GET", "/api/plugins"): "part 2: admin.py",
    ("GET", "/api/plugins/{name}"): "part 2: admin.py",
    ("GET", "/api/ai/status"): "part 2: admin.py",
    ("POST", "/api/ai/test"): "part 2: admin.py",
    ("GET", "/api/usage/me"): "part 2: admin.py",
    ("GET", "/api/admin/usage"): "part 2: admin.py",
    ("GET", "/api/index/embed-status"): "part 2: admin.py",
    ("GET", "/api/index/jobs"): "part 2: admin.py",
    ("GET", "/api/index/jobs/{job_id}"): "part 2: admin.py",
    ("POST", "/api/index/sync"): "part 2: admin.py",
    ("POST", "/api/site/render"): "part 2: admin.py",
    ("POST", "/api/kbs"): "part 2: admin.py -- KB registration, admin tier",
    ("PUT", "/api/kbs/{name}"): "part 2: admin.py",
    ("DELETE", "/api/kbs/{name}"): "part 2: admin.py",
    ("PUT", "/api/kbs/{name}/default-role"): "part 2: admin.py",
    ("GET", "/api/kbs/{name}/permissions"): "part 2: admin.py",
    ("POST", "/api/kbs/{name}/permissions"): "part 2: admin.py",
    ("POST", "/api/kbs/{name}/reindex"): "part 2: admin.py",
    ("GET", "/api/kbs/ephemeral"): "part 2: admin.py",
    ("POST", "/api/kbs/ephemeral"): "part 2: admin.py",
    ("DELETE", "/api/kbs/ephemeral/{name}"): "part 2: admin.py",
    ("POST", "/api/kbs/gc"): "part 2: admin.py",
    ("GET", "/api/settings"): "part 2: settings_ep.py",
    ("PUT", "/api/settings"): "part 2: settings_ep.py",
    ("GET", "/api/settings/{key}"): "part 2: settings_ep.py",
    ("PUT", "/api/settings/{key}"): "part 2: settings_ep.py",
    ("DELETE", "/api/settings/{key}"): "part 2: settings_ep.py",
    ("GET", "/api/repos"): "part 2: repos.py -- open PR #161 touches it",
    ("GET", "/api/repos/{name:path}"): "part 2: repos.py -- open PR #161 touches it",
    ("DELETE", "/api/repos/{name:path}"): "part 2: repos.py -- open PR #161 touches it",
    ("POST", "/api/repos/fork"): "part 2: repos.py -- open PR #161 touches it",
    ("POST", "/api/repos/subscribe"): "part 2: repos.py -- open PR #161 touches it",
    ("POST", "/api/repos/{name:path}/pr"): "part 2: repos.py -- open PR #161 touches it",
    ("POST", "/api/repos/{name:path}/sync"): "part 2: repos.py -- open PR #161 touches it",
    ("GET", "/api/github/repos"): "part 2: repos.py -- GitHub account listing, not KB content",
    ("GET", "/api/worktree/status"): "part 2: worktree.py",
    ("GET", "/api/worktree/changes"): "part 2: worktree.py",
    ("POST", "/api/worktree/reset"): "part 2: worktree.py",
    ("POST", "/api/worktree/submit"): "part 2: worktree.py",
    ("GET", "/api/admin/merge-queue"): "part 2: worktree.py",
    ("GET", "/api/admin/merge-queue/{username}/diff"): "part 2: worktree.py",
    ("POST", "/api/admin/merge-queue/{username}/merge"): "part 2: worktree.py",
    ("POST", "/api/admin/merge-queue/{username}/reject"): "part 2: worktree.py",
    (
        "GET",
        "/api/kbs/{kb_name}/changes",
    ): "part 2: git_ops.py -- tier check but no per-KB read check",
    ("POST", "/api/kbs/{kb_name}/commit"): "part 2: git_ops.py",
    ("POST", "/api/kbs/{kb_name}/publish"): "part 2: git_ops.py",
    ("POST", "/api/kbs/{kb_name}/push"): "part 2: git_ops.py",
    ("POST", "/api/kbs/{kb_name}/export"): "part 2: export route, kbs.py",
}

HOW_TO_FIX = """
Each route above serves data from a knowledge base without checking which
KBs the caller may read, so a private KB's content reaches a caller who
has no grant on it.

Scope it, in pyrite/server/endpoints/<module>.py:

  * names a KB (`kb` / `kb_name` in query, path or body) -->
        @router.get("/thing", dependencies=[Depends(requires_kb_read())])
    which answers 404 KB_NOT_FOUND -- never 403 -- for a KB the caller
    may not read, byte-identical to a KB that does not exist.

  * spans KBs (no kb parameter) -->
        readable: set[str] | None = Depends(get_readable_kbs)
    and push `kb_names=readable` into the service/query, as
    endpoints/search.py does. Filtering the rows in Python after the
    fact is not enough where a count, total or has_more would still
    reveal the private rows.

Both helpers live in pyrite/server/api.py. A route that genuinely serves
no KB content goes in ALLOWLIST in this file, with a reason.
"""


def _iter_api_routes():
    """Every (method, path, route) under /api in the real application.

    FastAPI's `include_router(prefix=...)` records an `_IncludedRouter`
    wrapper rather than flattening, and a router declared with
    `APIRouter(prefix=...)` has already baked that prefix into each
    `route.path`. So an including prefix is added only when the child
    paths do not already carry it. Cross-checked against `app.openapi()`
    in `test_route_walk_matches_openapi` below.
    """
    app = create_app()

    def walk(routes, prefix=""):
        found = []
        for route in routes:
            if type(route).__name__ == "_IncludedRouter":
                sub = route.original_router
                own = sub.prefix or ""
                children = walk(sub.routes, "")
                add = "" if (own and all(p.startswith(own) for p, _ in children)) else own
                found += [(prefix + add + p, r) for p, r in children]
            elif isinstance(route, APIRoute):
                found.append((prefix + route.path, route))
        return found

    out = []
    for path, route in walk(app.routes):
        if not path.startswith("/api"):
            continue
        for method in sorted(route.methods or ()):
            if method in ("HEAD", "OPTIONS"):
                continue
            out.append((method, path, route))
    return sorted(out, key=lambda t: (t[1], t[0]))


def _dependency_names(dependant) -> set[str]:
    """Qualified names of every dependency in a route's dependant tree."""
    names: set[str] = set()
    for dep in dependant.dependencies:
        call = dep.call
        module = getattr(call, "__module__", "?")
        qualname = getattr(call, "__qualname__", repr(call))
        names.add(f"{module}.{qualname}")
        names |= _dependency_names(dep)
    return names


def _is_scoped(route: APIRoute) -> bool:
    return bool(_dependency_names(route.dependant) & SCOPING_DEPENDENCIES)


def test_route_walk_matches_openapi():
    """The walk sees the same /api routes the app actually serves.

    Guards the walk itself: if FastAPI changes how included routers are
    recorded, this fails loudly rather than silently shrinking the set of
    routes the scoping test checks.
    """
    app = create_app()
    served = {p for p in app.openapi()["paths"] if p.startswith("/api")}
    # `{name:path}` in a route is `{name}` in the OpenAPI document.
    walked = {path.replace(":path}", "}") for _, path, _ in _iter_api_routes()}
    assert walked == served, (
        f"route walk disagrees with the served app\n"
        f"  only in walk:     {sorted(walked - served)}\n"
        f"  only in openapi:  {sorted(served - walked)}"
    )


def test_every_api_route_is_scoped_or_allowlisted():
    """No /api route reads KB content without a read-scoping dependency."""
    unscoped = [
        (method, path, route)
        for method, path, route in _iter_api_routes()
        if not _is_scoped(route) and (method, path) not in ALLOWLIST
    ]
    if unscoped:
        listing = "\n".join(
            f"  {method:6} {path:52} ({route.endpoint.__module__.rsplit('.', 1)[-1]}.py:"
            f"{route.endpoint.__name__})"
            for method, path, route in unscoped
        )
        raise AssertionError(
            f"{len(unscoped)} /api route(s) are not read-scoped:\n{listing}\n{HOW_TO_FIX}"
        )


def test_allowlist_entries_all_carry_a_reason():
    """An allowlist entry without a reason is a hole nobody can review."""
    missing = [key for key, reason in ALLOWLIST.items() if not (reason or "").strip()]
    assert not missing, f"allowlist entries with no reason: {missing}"


def test_allowlist_has_no_stale_entries():
    """An allowlisted route that no longer exists (or has since been scoped)
    must leave the allowlist, so the list stays an honest inventory of what
    part 2 still owes."""
    live = {(m, p) for m, p, _ in _iter_api_routes()}
    scoped = {(m, p) for m, p, r in _iter_api_routes() if _is_scoped(r)}
    gone = sorted(key for key in ALLOWLIST if key not in live)
    now_scoped = sorted(key for key in ALLOWLIST if key in scoped)
    assert not gone, f"allowlisted routes that no longer exist: {gone}"
    assert not now_scoped, (
        f"allowlisted routes that are now scoped -- remove them from ALLOWLIST: {now_scoped}"
    )
