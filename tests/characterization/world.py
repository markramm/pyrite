"""The one shared world every characterization case runs against (ADR-0037 theme 0).

One `PyriteConfig`, one `create_app()`, the ADR §5 KB axis -- readable,
private, a missing one that is simply never registered, and `NO_DEFAULT_ROLE`
(added to the axis per #476 blocker 5: the one state where a global user's
access and a local user's genuinely diverge, see below) -- plus one extra KB
the main matrix does not target (`READ_ONLY`, used by `test_error_bodies.py`'s
live cross-check only), and every principal the ADR §5.4 matrix names
(narrowed to the backlog item's concrete list), built once and shared by
every test in this package via a session-scoped fixture (`world`, in
`conftest.py`). Building it once keeps the ~68-operation x ~106-tool x
7-principal x 4-KB-state matrix inside the pre-push budget: this module does
the one-time setup, the test modules only read from it.

Principals (ADR-0037 §5, narrowed to the backlog item's concrete list):

- ``anonymous``   -- no credential at all.
- ``read_key``    -- an operator API key, role "read".
- ``write_key``   -- an operator API key, role "write".
- ``admin_key``   -- an operator API key, role "admin".
- ``global_user`` -- a session for a user seeded the operator's way
  (``AuthService.create_user``, what ``tests/auth_seed.py`` calls "the
  operator path"): ``global_access=True``, so their role covers every KB
  without a ``default_role``. Role "read".
- ``local_user``  -- a session for a *self-registered* user
  (``AuthService.register``, no invite code): ``global_access=False``. Gets
  ``read`` on the readable KB (its ``default_role``) and nothing on the
  private KB until granted -- this is the harness's stand-in for "without
  global access".
- ``granted_user`` -- a self-registered user (``global_access=False``) who
  was then given an explicit per-KB grant on the private KB
  (``AuthService.grant_kb_permission``) -- "with global access" is read as
  "with access", i.e. a grant that reaches the KB a bare self-registration
  cannot; see the report's Unsure note.

KBs:

- ``READABLE`` -- ``default_role="read"``: open to any authenticated (and,
  since ``anonymous_tier="read"``, anonymous) caller.
- ``PRIVATE``  -- ``default_role="none"``: exists, invisible without a
  grant or global access.
- ``MISSING``  -- a name no ``KBConfig`` registers. Never created on disk.
- ``READ_ONLY`` -- ``default_role="read"``, ``read_only=True``: readable by
  anyone READABLE is, but every write raises ``KBReadOnlyError`` -- used by
  `test_error_bodies.py`'s live cross-check, not the main matrix.
- ``NO_DEFAULT_ROLE`` -- `default_role` left unset (``None``): the one KB
  state where a global user's role (falls back to it) and a local user's
  (does not) actually diverge -- part of the main `KB_STATES` axis in
  `test_rest_matrix.py`/`test_mcp_matrix.py` (#476 blocker 5); see also
  `test_global_access.py`'s small, direct pair of cases pinning the
  mechanism by name.

Every principal is also given a matching MCP `readable_kbs`/`writable_kbs`
pair and API-key role, computed the same way REST resolves it
(`api.kbs_for_user_at_tier`), so the REST and MCP goldens exercise the same
world through the same identities.
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db, kbs_for_user_at_tier
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.services.auth_service import AuthService
from pyrite.services.index_worker import IndexWorker
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from tests.auth_seed import SESSION_COOKIE, seed_user, sign_in

READABLE = "readable-kb"
PRIVATE = "private-kb"
READ_ONLY = "read-only-kb"
MISSING = "missing-kb"  # never registered -- a name, not a KBConfig

# A fourth KB, outside the ADR §5 {readable, private, missing} axis: its
# `default_role` is unset (None), which is the one state where "global
# access" and "no global access" actually diverge (`AuthService.get_kb_role`:
# a `default_role="none"` KB, PRIVATE above, is closed to global and local
# alike; a KB with NO default_role falls back to the caller's global role,
# but only when `global_access` is set). Used only by the
# global-vs-local-access case, not the main principal x KB-state matrix.
NO_DEFAULT_ROLE = "no-default-role-kb"

READABLE_ENTRY = "readable-note"
PRIVATE_ENTRY = "private-note"
READ_ONLY_ENTRY = "read-only-note"
NO_DEFAULT_ROLE_ENTRY = "no-default-role-note"

READ_KEY = "characterization-read-key"
WRITE_KEY = "characterization-write-key"
ADMIN_KEY = "characterization-admin-key"


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass(frozen=True)
class Principal:
    """One row of the ADR §5.4 matrix, as something a test can hand to a
    REST `TestClient` call, an MCP `_dispatch_tool` call, or a CLI
    invocation."""

    name: str
    kind: str  # "anonymous" | "api_key" | "session"
    rest_headers: dict[str, str]
    rest_cookies: dict[str, str]
    readable_kbs: frozenset[str] | None  # None == unscoped (admin/operator)
    writable_kbs: frozenset[str] | None
    user_id: int | None = None


@dataclass
class World:
    """Everything a characterization case reads. Built once per session."""

    tmpdir: Path
    config: PyriteConfig
    app: Any
    client: TestClient  # unauthenticated base client; principals set headers/cookies per call
    db: PyriteDB
    index_worker: IndexWorker
    mcp_server: PyriteMCPServer
    principals: dict[str, Principal]

    def close(self) -> None:
        self.index_worker.wait_for_idle(timeout=10)
        self.mcp_server.close()
        self.db.close()

    def release_idle_connections(self) -> None:
        """Close and clear this world's DB's per-thread fallback SQLAlchemy
        sessions, releasing their pooled connections without disposing the
        engine (unlike `db.close()`, which the run isn't done with yet).

        Found while building this harness, not part of the theme: REST's
        `get_db` override (this world's, and the same pattern
        `tests/test_api_tiers.py::_build_client` and every other
        `TestClient`-based test uses) hands every request the bare shared
        `PyriteDB`, bypassing `request_handle()`'s per-request session that
        closes on teardown (`pyrite/storage/connection.py`). Each distinct
        thread FastAPI's anyio threadpool uses to serve a sync `def` handler
        then falls into `PyriteDB.session`'s per-thread **fallback** branch,
        which opens a session -- and holds its pooled connection -- for the
        life of that thread, not that request. `HANDLER_CONCURRENCY_LIMIT`
        (40) plus `_MAX_OVERFLOW` (20) covers ordinary test traffic; this
        harness's ~3,600 REST+MCP calls exhausts it, and the request that
        finds the pool empty hangs forever (`sqlalchemy.util.queue.Queue.get`
        with no timeout) rather than erroring -- confirmed with
        `faulthandler` mid-hang while building this harness. Calling this
        before every REST call (MCP's direct `_dispatch_tool`
        calls run on one thread and do not hit this) keeps the pool's
        headroom ahead of the leak. The leak itself is pre-existing
        infrastructure, out of this theme's scope; reported, not fixed here.
        """
        with self.db._fallback_lock:
            sessions, self.db._fallback_sessions = self.db._fallback_sessions, []
        for session in sessions:
            try:
                session.close()
            except Exception:  # pragma: no cover - defensive, mirrors PyriteDB.close
                pass


def build_world(tmp_path_factory) -> World:
    tmpdir = Path(tmp_path_factory.mktemp("adr0037-characterization"))
    for name in (READABLE, PRIVATE, READ_ONLY, NO_DEFAULT_ROLE):
        (tmpdir / name).mkdir()

    keys = [
        {"key_hash": _hash_key(READ_KEY), "role": "read", "label": "characterization-read"},
        {"key_hash": _hash_key(WRITE_KEY), "role": "write", "label": "characterization-write"},
        {"key_hash": _hash_key(ADMIN_KEY), "role": "admin", "label": "characterization-admin"},
    ]
    config = PyriteConfig(
        knowledge_bases=[
            KBConfig(name=READABLE, path=tmpdir / READABLE, kb_type="generic", default_role="read"),
            KBConfig(name=PRIVATE, path=tmpdir / PRIVATE, kb_type="generic", default_role="none"),
            KBConfig(
                name=READ_ONLY,
                path=tmpdir / READ_ONLY,
                kb_type="generic",
                default_role="read",
                read_only=True,
            ),
            KBConfig(name=NO_DEFAULT_ROLE, path=tmpdir / NO_DEFAULT_ROLE, kb_type="generic"),
        ],
        settings=Settings(
            index_path=tmpdir / "index.db",
            api_keys=keys,
            auth=AuthConfig(enabled=True, allow_registration=True, anonymous_tier="read"),
        ),
    )

    app = create_app(config=config)
    db = PyriteDB(config.settings.index_path)
    app.dependency_overrides[get_config] = lambda: config
    app.dependency_overrides[get_db] = lambda: db
    index_worker = IndexWorker(db, config)

    from pyrite.server.api import get_index_worker

    app.dependency_overrides[get_index_worker] = lambda: index_worker

    kb_service = KBService(config, db)
    kb_service.create_entry(
        READABLE, READABLE_ENTRY, "Readable note", "note", "a zebra in the open"
    )
    kb_service.create_entry(
        PRIVATE, PRIVATE_ENTRY, "Private note", "note", "a zebra behind the wall"
    )
    # KBService's write path refuses a read-only KB by construction (the
    # very behaviour theme 0 pins), so this one entry is written to disk
    # directly and picked up by a sync -- the same as any KB an operator
    # marks read-only after content already exists.
    (tmpdir / READ_ONLY / f"{READ_ONLY_ENTRY}.md").write_text(
        "---\n"
        f"id: {READ_ONLY_ENTRY}\n"
        "type: note\n"
        "title: Read-only note\n"
        "---\n\n"
        "a zebra that cannot be moved\n"
    )
    index_worker.submit_sync(READ_ONLY)
    index_worker.wait_for_idle(timeout=10)
    kb_service.create_entry(
        NO_DEFAULT_ROLE,
        NO_DEFAULT_ROLE_ENTRY,
        "No-default-role note",
        "note",
        "a zebra of no fixed abode",
    )

    client = TestClient(app)

    # anonymous's readable/writable sets: computed the same way REST resolves
    # them (`kbs_for_user_at_tier(..., user_id=None, role=None, ...)`), not
    # hand-listed -- a hand-listed set silently drifts from the real ceiling
    # rule (`anonymous_tier` covers a KB with NO default_role too, which is
    # easy to get wrong by inspection alone).
    anon_readable = kbs_for_user_at_tier(config, db, None, None, "read")
    anon_writable = kbs_for_user_at_tier(config, db, None, None, "write")

    # -- operator API keys: unscoped (an operator key is not a peer) --------
    principals: dict[str, Principal] = {
        "anonymous": Principal(
            "anonymous",
            "anonymous",
            {},
            {},
            readable_kbs=frozenset(anon_readable) if anon_readable is not None else None,
            writable_kbs=frozenset(anon_writable) if anon_writable is not None else None,
        ),
        "read_key": Principal(
            "read_key", "api_key", {"X-API-Key": READ_KEY}, {}, readable_kbs=None, writable_kbs=None
        ),
        "write_key": Principal(
            "write_key",
            "api_key",
            {"X-API-Key": WRITE_KEY},
            {},
            readable_kbs=None,
            writable_kbs=None,
        ),
        "admin_key": Principal(
            "admin_key",
            "api_key",
            {"X-API-Key": ADMIN_KEY},
            {},
            readable_kbs=None,
            writable_kbs=None,
        ),
    }

    # -- sessions: seeded through AuthService, the way tests/auth_seed.py's
    # docstring describes as "the operator path" for a global user, and
    # through the real self-registration path (allow_registration=True
    # above) for the two without global access. -----------------------------
    auth_service = AuthService(db, config.settings.auth)

    # global_user: first user in this DB -> seed_user makes it "admin"
    # unless a role is given; we want a *non*-admin global user, so create
    # the admin first (unused as a principal directly; admin_key already
    # covers the admin-key case) and then a global "read" user explicitly.
    admin_row = seed_user(db, "characterization-admin-user", role="admin")
    global_row = seed_user(db, "characterization-global-user", role="read")
    # seed_user's "later users get read, global" default already sets
    # global_access=True (tests/auth_seed.py's documented contract).

    local_row = auth_service.register("characterization-local-user", "password123")
    granted_row = auth_service.register("characterization-granted-user", "password456")
    auth_service.grant_kb_permission(granted_row["id"], PRIVATE, "read", granted_by=admin_row["id"])

    def _session_principal(name: str, username: str, password: str, user_id: int) -> Principal:
        token = sign_in(app, username, password)
        role = auth_service.get_user(user_id)["role"]
        readable = kbs_for_user_at_tier(config, db, user_id, role, "read")
        writable = kbs_for_user_at_tier(config, db, user_id, role, "write")
        return Principal(
            name,
            "session",
            {},
            {SESSION_COOKIE: token},
            readable_kbs=frozenset(readable) if readable is not None else None,
            writable_kbs=frozenset(writable) if writable is not None else None,
            user_id=user_id,
        )

    principals["global_user"] = _session_principal(
        "global_user", "characterization-global-user", "password123", global_row["id"]
    )
    principals["local_user"] = _session_principal(
        "local_user", "characterization-local-user", "password123", local_row["id"]
    )
    principals["granted_user"] = _session_principal(
        "granted_user", "characterization-granted-user", "password456", granted_row["id"]
    )

    mcp_server = PyriteMCPServer(config=config, tier="admin")

    return World(
        tmpdir=tmpdir,
        config=config,
        app=app,
        client=client,
        db=db,
        index_worker=index_worker,
        mcp_server=mcp_server,
        principals=principals,
    )
