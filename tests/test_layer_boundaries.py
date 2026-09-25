"""The surfaces reach storage only through services -- a ratchet (#380).

REST (`pyrite/server`), MCP (`pyrite/server/mcp_server.py`), the CLIs
(`pyrite/cli`, `pyrite/admin_cli.py`, `pyrite/read_cli.py`) and the
Streamlit UI (`pyrite/ui`) are *surfaces*. ADR-0031 makes the API the
product surface; that holds only if behaviour lives in one layer, so a
surface asks a service and the service asks storage. This file walks the
AST of every module under `pyrite/` outside `pyrite/services` and
`pyrite/storage` and fails on any of these reaches:

========================  ==================================================
rule                      what it catches
========================  ==================================================
``_raw_conn``             the raw sqlite connection, anywhere
``.db.``                  ``<anything>.db.<attr>`` -- a service's or a
                          context's database handle, reached through
``db.call(``              ``db.<method>(...)`` on a local ``db``, other
                          than ``db.close()``
``PyriteDB(``             opening the database
``Depends(get_db)``       a request-scoped DB handle, outside ``api.py``
``AuthService(``          building the auth service inline, outside
                          ``api.py`` (take it from ``get_auth_service``)
``.pyrite_db``            the app's shared DB on ``app.state``, outside
                          ``api.py``
========================  ==================================================

Two lists name the functions allowed to offend, **by function, not line**:

- ``COMPOSITION_ROOTS``: where a surface opens the database and builds its
  services -- ``api.py``'s ``get_db``/``_app_db`` family, ``cli/context.py``,
  the MCP server's constructor, the UI's cached ``_get_db``. That is the
  job; #382 (the composition root) is where they converge.
- ``ALLOWLIST``: offenders not yet moved, each with the issue that moves
  it. **It only shrinks.** An entry that no longer offends fails the
  test until it is deleted, and ``ALLOWLIST_SIZE`` must equal its length,
  so adding an entry means raising a number a reviewer will see.

A third check uses the shared entry-point inventory
(`tests/_surface_inventory.py`, ADR-0037): every REST operation and MCP
tool handler lives in a module this scan covers, or in `extensions/`
(extension code is #384's, and outside this ratchet).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests._surface_inventory import REPO_ROOT, mcp_server, mcp_tools, rest_operations


PACKAGE = REPO_ROOT / "pyrite"
LAYERS_BELOW_THE_SURFACES = ("pyrite/services/", "pyrite/storage/")
PROVIDER_MODULE = "pyrite/server/api.py"  # Depends(get_db), AuthService(, .pyrite_db

# Where a surface opens the database and wires its services. Exempt from
# every rule; each must still exist and still offend (else delete it).
COMPOSITION_ROOTS: dict[str, str] = {
    "pyrite/server/api.py::get_db": "the request DB provider every other provider depends on",
    "pyrite/server/api.py::get_index_mgr": "non-app fallback provider (overridden in create_app)",
    "pyrite/server/api.py::get_index_worker": "non-app fallback provider (overridden in create_app)",
    "pyrite/server/api.py::create_app._app_db": "the app's one PyriteDB, built and cached on app state",
    "pyrite/server/api.py::create_app._app_get_db": "the per-request session handle (#131)",
    "pyrite/server/mcp_server.py::PyriteMCPServer.__init__": "the MCP server's composition root (#382)",
    "pyrite/server/mcp_server.py::PyriteMCPServer.close": "closes what __init__ opened",
    "pyrite/cli/context.py::get_config_and_db": "the CLI provider (opens + merges DB-registered KBs)",
    "pyrite/cli/context.py::get_config_with_registered_kbs": "the CLI's KB-name resolver fallback",
    "pyrite/cli/context.py::open_index_db": "the CLI provider for commands that never merged KBs",
    "pyrite/ui/data.py::_get_db": "the Streamlit UI's cached DB, from which _get_kb_service is built",
}

# (function, rule) pairs still reaching past the services. Shrink only.
ALLOWLIST: dict[tuple[str, str], str] = {
    ("pyrite/server/api.py::get_llm_service", "db.call("): (
        "the AI-settings precedence (DB setting over config); deferred from #380 until after "
        "the patch release, moves to SettingsService with the composition root (#382)"
    ),
    ("pyrite/server/api.py::resolve_kb_default_role", "_raw_conn"): (
        "authorization: moves to services/access_policy.py and reads through the KB "
        "registry (#383, ADR-0037 theme 1)"
    ),
    ("pyrite/server/api.py::kb_exists", "_raw_conn"): (
        "authorization (the concealment check): moves with resolve_kb_default_role (#383)"
    ),
    ("pyrite/server/mcp_routes.py::_resolve_credential", "AuthService("): (
        "MCP credential resolution: #433 rewrote it; Principal construction moves to the "
        "policy (#383, ADR-0037 theme 4)"
    ),
    ("pyrite/plugins/context.py::PluginContext.search_semantic", ".db."): (
        "the plugin API's context holds the DB for plugins (reads vec_available before "
        "building EmbeddingService); the plugin contract is #384's"
    ),
}
ALLOWLIST_SIZE = 5  # lower it with every entry removed; never raise it

RULES = (
    "_raw_conn",
    ".db.",
    "db.call(",
    "PyriteDB(",
    "Depends(get_db)",
    "AuthService(",
    ".pyrite_db",
)


_SELF_TEST = pytest.mark.control(
    reason="tests the ratchet itself (its scanner, allowlist bookkeeping or the shared inventory), which this PR adds: true on either side of the change"
)


def find_reaches(source: str, rel: str) -> dict[tuple[str, str], int]:
    """{(``rel::qualname``, rule): count} for every reach in ``source``."""
    found: dict[tuple[str, str], int] = {}
    stack: list[str] = []
    in_provider_module = rel == PROVIDER_MODULE

    def hit(rule: str) -> None:
        key = (f"{rel}::{'.'.join(stack) or '<module>'}", rule)
        found[key] = found.get(key, 0) + 1

    class Visitor(ast.NodeVisitor):
        def _scoped(self, node):
            stack.append(node.name)
            self.generic_visit(node)
            stack.pop()

        def visit_FunctionDef(self, node):  # noqa: N802 -- ast.NodeVisitor's names
            self._scoped(node)

        def visit_AsyncFunctionDef(self, node):  # noqa: N802
            self._scoped(node)

        def visit_ClassDef(self, node):  # noqa: N802
            self._scoped(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if node.attr == "_raw_conn":
                hit("_raw_conn")
            if isinstance(node.value, ast.Attribute) and node.value.attr == "db":
                hit(".db.")
            if node.attr == "pyrite_db" and not in_provider_module:
                hit(".pyrite_db")
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            fn = node.func
            name = (
                fn.id
                if isinstance(fn, ast.Name)
                else fn.attr
                if isinstance(fn, ast.Attribute)
                else None
            )
            if name == "PyriteDB":
                hit("PyriteDB(")
            if (
                name == "AuthService"
                and rel.startswith("pyrite/server/")
                and not in_provider_module
            ):
                hit("AuthService(")
            if (
                isinstance(fn, ast.Attribute)
                and isinstance(fn.value, ast.Name)
                and fn.value.id == "db"
                and fn.attr != "close"
            ):
                hit("db.call(")
            if (
                name == "Depends"
                and not in_provider_module
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "get_db"
            ):
                hit("Depends(get_db)")
            self.generic_visit(node)

    Visitor().visit(ast.parse(source))
    return found


def _scanned_modules() -> list[Path]:
    return [
        p
        for p in sorted(PACKAGE.rglob("*.py"))
        if not p.relative_to(REPO_ROOT).as_posix().startswith(LAYERS_BELOW_THE_SURFACES)
    ]


@pytest.fixture(scope="module")
def reaches() -> dict[tuple[str, str], int]:
    found: dict[tuple[str, str], int] = {}
    for path in _scanned_modules():
        rel = path.relative_to(REPO_ROOT).as_posix()
        found.update(find_reaches(path.read_text(), rel))
    return found


def test_no_surface_reaches_past_the_services(reaches):
    offenders = sorted(
        f"{where}  [{rule}] x{count}"
        for (where, rule), count in reaches.items()
        if where not in COMPOSITION_ROOTS and (where, rule) not in ALLOWLIST
    )
    assert not offenders, (
        "these reach storage without going through a service -- add or use a "
        "service method (and a provider in api.py / cli/context.py), do not "
        "allowlist them:\n  " + "\n  ".join(offenders)
    )


@_SELF_TEST
def test_allowlist_has_no_stale_entries(reaches):
    stale = sorted(f"{where} [{rule}]" for where, rule in ALLOWLIST if (where, rule) not in reaches)
    assert not stale, (
        "allowlisted reaches that no longer happen -- delete them and lower "
        "ALLOWLIST_SIZE:\n  " + "\n  ".join(stale)
    )


@_SELF_TEST
def test_allowlist_only_shrinks():
    assert len(ALLOWLIST) == ALLOWLIST_SIZE, (
        f"ALLOWLIST has {len(ALLOWLIST)} entries but ALLOWLIST_SIZE is {ALLOWLIST_SIZE}. "
        "Removing an entry: lower ALLOWLIST_SIZE to match. Adding one is not the fix; "
        "route the reach through a service."
    )
    assert all(reason.strip() for reason in ALLOWLIST.values())
    assert {rule for _, rule in ALLOWLIST} <= set(RULES)


def test_composition_roots_are_real_and_needed(reaches):
    offending = {where for where, _ in reaches}
    unneeded = sorted(set(COMPOSITION_ROOTS) - offending)
    assert not unneeded, (
        "listed composition roots that open no database any more (or no longer "
        "exist) -- delete them:\n  " + "\n  ".join(unneeded)
    )


# -- The rules themselves: each catches what it says it does -----------------


@_SELF_TEST
@pytest.mark.parametrize(
    ("snippet", "rule"),
    [
        ("def h(svc):\n    return svc.db.get_setting('k')\n", ".db."),
        ("def h(svc):\n    svc.db.session.query(X)\n", ".db."),
        ("def h(db):\n    return db.count_entries()\n", "db.call("),
        ("def h(db):\n    db._raw_conn.execute('SELECT 1')\n", "_raw_conn"),
        ("def h(c):\n    return PyriteDB(c.settings.index_path)\n", "PyriteDB("),
        ("def h(db=Depends(get_db)):\n    pass\n", "Depends(get_db)"),
        ("def h(db, c):\n    return AuthService(db, c.settings.auth)\n", "AuthService("),
        ("def h(request):\n    return request.app.state.pyrite_db\n", ".pyrite_db"),
    ],
)
def test_each_rule_catches_its_reach(snippet, rule):
    found = find_reaches(snippet, "pyrite/server/endpoints/new_endpoint.py")
    assert found == {("pyrite/server/endpoints/new_endpoint.py::h", rule): 1}


@_SELF_TEST
def test_a_new_endpoint_touching_db_fails_the_ratchet(reaches):
    """The ticket's acceptance: the test fails when a new endpoint touches `.db.`."""
    new = find_reaches(
        "def get_thing(svc=Depends(get_kb_service)):\n    return svc.db.get_all_settings()\n",
        "pyrite/server/endpoints/things.py",
    )
    combined = {**reaches, **new}
    with pytest.raises(AssertionError, match=r"things.py::get_thing  \[\.db\.\]"):
        test_no_surface_reaches_past_the_services(combined)


@_SELF_TEST
@pytest.mark.parametrize(
    "snippet",
    [
        "def h(db):\n    db.close()\n",
        "def h(svc):\n    return svc.get_setting('k')\n",
        "def h(self):\n    return KBService(self.config, self.db)\n",
    ],
)
def test_what_the_rules_do_not_catch(snippet):
    """Closing a handle, calling a service, and handing a DB to a service
    constructor are not reaches."""
    assert find_reaches(snippet, "pyrite/cli/x.py") == {}


@_SELF_TEST
def test_the_provider_module_may_take_get_db_and_build_auth_service():
    src = "def get_x(db=Depends(get_db)):\n    return AuthService(db, None)\n"
    assert find_reaches(src, PROVIDER_MODULE) == {}
    assert set(find_reaches(src, "pyrite/server/endpoints/x.py")) == {
        ("pyrite/server/endpoints/x.py::get_x", "Depends(get_db)"),
        ("pyrite/server/endpoints/x.py::get_x", "AuthService("),
    }


# -- Coverage: the scan sees every entry point -------------------------------


def _is_scanned(source: Path | None) -> bool:
    if source is None or source.is_absolute():
        return False
    rel = source.as_posix()
    return rel.startswith("pyrite/") and not rel.startswith(LAYERS_BELOW_THE_SURFACES)


@_SELF_TEST
def test_every_rest_operation_is_in_a_scanned_module():
    ops = rest_operations()
    assert len(ops) > 100  # the walk found the app, not a stub
    unscanned = sorted(f"{op.name} -> {op.source}" for op in ops if not _is_scanned(op.source))
    assert not unscanned, "REST handlers outside the scanned surfaces:\n  " + "\n  ".join(unscanned)


@_SELF_TEST
def test_every_mcp_tool_is_in_a_scanned_module_or_an_extension():
    with mcp_server() as server:
        tools = mcp_tools(server)
    assert len(tools) > 50
    unscanned = sorted(
        f"{t.name} -> {t.source}"
        for t in tools
        if not _is_scanned(t.source)
        and not (t.source and t.source.as_posix().startswith("extensions/"))
    )
    assert not unscanned, "MCP tool handlers outside the scanned surfaces:\n  " + "\n  ".join(
        unscanned
    )
