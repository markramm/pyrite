"""An ephemeral KB's private access policy survives a restart.

A user's ephemeral KB is created with ``default_role: none``: only the creator
(through their per-KB admin grant) and global admins may use it. That policy
must be written with the KB -- to the registry row and to ``config.yaml`` --
in the same step that creates it, so that every process (a restarted server,
a second worker, the CLI) resolves the same policy.

The restart is simulated by constructing the app a second time from the
config file and database the first app wrote.
"""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import pyrite.config as config_module
from pyrite.config import AuthConfig, PyriteConfig, Settings, load_config, save_config
from pyrite.server.api import create_app
from pyrite.services.auth_service import AuthService
from pyrite.services.ephemeral_service import EphemeralKBService
from pyrite.storage.database import PyriteDB


def _fresh_config(tmp: Path) -> PyriteConfig:
    config = PyriteConfig(
        knowledge_bases=[],
        settings=Settings(
            index_path=tmp / "index.db",
            workspace_path=tmp / "workspace",
            auth=AuthConfig(enabled=True, allow_registration=True),
        ),
    )
    save_config(config)
    return config


def _register(app, username) -> dict:
    client = TestClient(app)
    r = client.post("/auth/register", json={"username": username, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"pyrite_session": r.cookies["pyrite_session"]}


@pytest.fixture
def first_boot(tmp_path):
    """Boot 1: alice (write) creates an ephemeral KB and writes an entry in it."""
    config = _fresh_config(tmp_path)
    app = create_app(config=config)
    cookies = {name: _register(app, name) for name in ("admin", "alice", "bob")}
    db = PyriteDB(config.settings.index_path)
    try:
        auth = AuthService(db, config.settings.auth)
        users = {u["username"]: u["id"] for u in auth.list_users()}
        auth.set_role(users["alice"], "write")
        auth.set_role(users["bob"], "write")
    finally:
        db.close()

    alice = TestClient(app, cookies=cookies["alice"])
    r = alice.post("/api/kbs/ephemeral", json={"name": "scratch"})
    assert r.status_code == 200, r.text
    # A non-admin's REST write goes through a per-user git worktree, which an
    # ephemeral KB does not have; index the entry directly instead.
    db = PyriteDB(config.settings.index_path)
    try:
        db.upsert_entry(
            {
                "id": "private-note",
                "kb_name": "scratch",
                "entry_type": "note",
                "title": "Private note",
                "body": "x",
                "file_path": str(config.get_kb("scratch").path / "private-note.md"),
            }
        )
    finally:
        db.close()

    # Before the restart the KB is already private to alice.
    bob = TestClient(app, cookies=cookies["bob"])
    assert bob.get("/api/kbs/scratch").status_code == 404
    return {"tmp": tmp_path, "cookies": cookies}


def _restart():
    """A new process: config from the file on disk, a new app over the same DB."""
    return create_app(config=load_config())


def test_other_user_cannot_read_ephemeral_kb_after_restart(first_boot):
    app = _restart()
    bob = TestClient(app, cookies=first_boot["cookies"]["bob"])

    assert bob.get("/api/kbs/scratch").status_code == 404
    assert bob.get("/api/entries", params={"kb": "scratch"}).status_code == 404


def test_other_user_cannot_write_ephemeral_kb_after_restart(first_boot):
    app = _restart()
    bob = TestClient(app, cookies=first_boot["cookies"]["bob"])

    r = bob.post("/api/entries", json={"kb": "scratch", "title": "Intruder", "body": "x"})
    assert r.status_code == 404, r.text


def test_creator_keeps_access_after_restart(first_boot):
    app = _restart()
    alice = TestClient(app, cookies=first_boot["cookies"]["alice"])

    assert alice.get("/api/kbs/scratch").status_code == 200
    r = alice.get("/api/entries", params={"kb": "scratch"})
    assert r.status_code == 200, r.text


def test_policy_is_in_the_registry_row_and_the_config_file(first_boot):
    """Each of the two stores carries the policy on its own."""
    db = PyriteDB(first_boot["tmp"] / "index.db")
    try:
        rows = db.execute_sql("SELECT default_role FROM kb WHERE name = 'scratch'")
    finally:
        db.close()
    assert rows and rows[0]["default_role"] == "none"

    data = config_module.load_yaml_file(config_module.current_config_file())
    kb = next(k for k in data["knowledge_bases"] if k["name"] == "scratch")
    assert kb.get("default_role") == "none"


class TestGrantCommitsWithTheKB:
    """The creator's grant and the KB row land together, or neither does."""

    def _setup(self, tmp_path):
        config = _fresh_config(tmp_path)
        db = PyriteDB(config.settings.index_path)
        auth = AuthService(db, config.settings.auth)
        auth.register("admin", "password123")  # first user: the sole admin
        user = auth.register("alice", "password123")
        auth.set_role(user["id"], "write")
        return config, db, auth, user

    def test_failure_after_create_leaves_no_kb_and_no_grant(self, tmp_path):
        config, db, auth, user = self._setup(tmp_path)
        try:
            # A real database failure on the second of the two writes, so the
            # session is left needing a rollback, as it would be in production.
            db.execute_write_sql(
                "CREATE TRIGGER fail_count BEFORE UPDATE OF ephemeral_kb_count ON local_user"
                " BEGIN SELECT RAISE(ABORT, 'simulated failure'); END"
            )
            with pytest.raises(Exception, match="simulated failure"):
                auth.create_user_ephemeral_kb(user["id"], EphemeralKBService(config, db), "gone")

            assert config.get_kb("gone") is None
            assert db.execute_sql("SELECT 1 FROM kb WHERE name = 'gone'") == []
            assert db.execute_sql("SELECT 1 FROM kb_permission WHERE kb_name = 'gone'") == []
            assert not (tmp_path / "workspace" / "ephemeral" / "gone").exists()
            names = [k["name"] for k in load_config().to_dict()["knowledge_bases"]]
            assert "gone" not in names
        finally:
            db.close()

    def test_success_commits_grant_and_count(self, tmp_path):
        config, db, auth, user = self._setup(tmp_path)
        try:
            auth.create_user_ephemeral_kb(user["id"], EphemeralKBService(config, db), "kept")
        finally:
            db.close()
        # A second connection sees both: nothing is left pending in the first.
        db2 = PyriteDB(tmp_path / "index.db")
        try:
            grants = db2.execute_sql("SELECT role FROM kb_permission WHERE kb_name = 'kept'")
            count = db2.execute_sql(
                "SELECT ephemeral_kb_count FROM local_user WHERE id = :u", {"u": user["id"]}
            )
        finally:
            db2.close()
        assert grants == [{"role": "admin"}]
        assert count[0]["ephemeral_kb_count"] == 1


class TestRepairOfEphemeralKBsWithoutPolicy:
    """Ephemeral KBs written by an earlier version have no default_role at all."""

    def _write_legacy_config(self, tmp_path):
        (tmp_path / "workspace" / "ephemeral" / "old").mkdir(parents=True)
        config = _fresh_config(tmp_path)
        data = config.to_dict()
        data["knowledge_bases"] = [
            {
                "name": "old",
                "path": str(tmp_path / "workspace" / "ephemeral" / "old"),
                "kb_type": "generic",
                "ephemeral": True,
                "ttl": 3600,
                "created_at_ts": 9999999999.0,
            },
            {"name": "plain", "path": str(tmp_path / "plain"), "kb_type": "generic"},
        ]
        config_module.dump_yaml_file(data, config_module.current_config_file())

    def test_legacy_ephemeral_kb_is_private_on_load(self, tmp_path, caplog):
        self._write_legacy_config(tmp_path)
        with caplog.at_level(logging.WARNING, logger="pyrite.config"):
            config = load_config()
        assert config.get_kb("old").default_role == "none"
        assert any("old" in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)

    def test_repair_leaves_non_ephemeral_kbs_alone(self, tmp_path):
        self._write_legacy_config(tmp_path)
        config = load_config()
        assert config.get_kb("plain").default_role is None

    def test_legacy_ephemeral_kb_is_hidden_from_other_users_through_the_app(self, tmp_path):
        self._write_legacy_config(tmp_path)
        app = create_app(config=load_config())
        bob = TestClient(app, cookies=_register(app, "admin") and _register(app, "bob"))
        assert bob.get("/api/kbs/old").status_code == 404


def test_ephemeral_kb_created_without_a_user_is_persisted_private(tmp_path):
    """The admin endpoint and the CLI create ephemeral KBs with no creator grant.

    They are private by default too, and the default is persisted, not
    applied later: the registry row and config.yaml carry "none".
    """
    config = _fresh_config(tmp_path)
    db = PyriteDB(config.settings.index_path)
    try:
        EphemeralKBService(config, db).create_ephemeral_kb("adminscratch")
        rows = db.execute_sql("SELECT default_role FROM kb WHERE name = 'adminscratch'")
    finally:
        db.close()
    assert rows[0]["default_role"] == "none"
    data = config_module.load_yaml_file(config_module.current_config_file())
    kb = next(k for k in data["knowledge_bases"] if k["name"] == "adminscratch")
    assert kb.get("default_role") == "none"


class TestRepairOfEphemeralRegistryRowsWithoutConfig:
    """A pre-fix ephemeral KB whose config.yaml entry was lost.

    Only its registry row survives: no ephemeral flag, default_role NULL. The
    registry merge brought it back readable at every user's global role. A
    registry row whose path is under <workspace>/ephemeral/ is an ephemeral
    KB's, and one without a policy is made private when it is loaded.
    """

    def _orphan(self, tmp_path, monkeypatch):
        # The workspace is not stored in config.yaml; a deployment sets it with
        # PYRITE_DATA_DIR (index at <dir>/index.db, workspace at <dir>/repos),
        # which both processes here share.
        monkeypatch.setenv("PYRITE_DATA_DIR", str(tmp_path))
        config = PyriteConfig(
            knowledge_bases=[],
            settings=Settings(
                index_path=tmp_path / "index.db",
                workspace_path=tmp_path / "repos",
                auth=AuthConfig(enabled=True, allow_registration=True),
            ),
        )
        save_config(config)
        app = create_app(config=config)
        cookies = {name: _register(app, name) for name in ("admin", "alice", "bob")}
        db = PyriteDB(config.settings.index_path)
        try:
            auth = AuthService(db, config.settings.auth)
            users = {u["username"]: u["id"] for u in auth.list_users()}
            auth.set_role(users["alice"], "write")
            auth.set_role(users["bob"], "write")
            auth.create_user_ephemeral_kb(users["alice"], EphemeralKBService(config, db), "lost")
            # The state an earlier version leaves: no policy in the row, and
            # the config entry gone (hand-edited, or written by another process).
            db.execute_write_sql("UPDATE kb SET default_role = NULL WHERE name = 'lost'")
            outside = tmp_path / "elsewhere"
            outside.mkdir()
            db.register_kb("open-kb", "generic", str(outside))
            # A KB at the ephemeral root itself is not an ephemeral KB.
            db.register_kb("root-kb", "generic", str(tmp_path / "repos" / "ephemeral"))
        finally:
            db.close()
        config.remove_kb("lost")
        save_config(config)
        return cookies

    def test_orphaned_row_is_private_after_restart(self, tmp_path, monkeypatch, caplog):
        cookies = self._orphan(tmp_path, monkeypatch)
        with caplog.at_level(logging.WARNING):
            config = load_config()
            assert config.settings.workspace_path == (tmp_path / "repos").resolve()
            assert config.get_kb("lost") is None
            app = create_app(config=config)
            bob = TestClient(app, cookies=cookies["bob"])
            assert bob.get("/api/kbs/lost").status_code == 404
            assert bob.get("/api/entries", params={"kb": "lost"}).status_code == 404
        assert any("lost" in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
        alice = TestClient(app, cookies=cookies["alice"])
        assert alice.get("/api/kbs/lost").status_code == 200

        db = PyriteDB(tmp_path / "index.db")
        try:
            rows = db.execute_sql("SELECT default_role FROM kb WHERE name = 'lost'")
            other = db.execute_sql("SELECT default_role FROM kb WHERE name = 'open-kb'")
            root_row = db.execute_sql("SELECT default_role FROM kb WHERE name = 'root-kb'")
        finally:
            db.close()
        assert rows[0]["default_role"] == "none"
        # A registry row outside the ephemeral root is left alone.
        assert other[0]["default_role"] is None
        assert root_row[0]["default_role"] is None

    def test_repair_is_committed_by_the_process_that_loads(self, tmp_path, monkeypatch):
        """A read-only process (the CLI, MCP stdio) also persists the repair."""
        self._orphan(tmp_path, monkeypatch)
        config = load_config()
        db = PyriteDB(tmp_path / "index.db")
        try:
            db.merge_registered_kbs(config)
            assert config.get_kb("lost").default_role == "none"
        finally:
            db.close()
        other = PyriteDB(tmp_path / "index.db")
        try:
            rows = other.execute_sql("SELECT default_role FROM kb WHERE name = 'lost'")
        finally:
            other.close()
        assert rows[0]["default_role"] == "none"

    def test_a_repair_that_cannot_write_still_loads_the_kb_private(self, tmp_path, monkeypatch):
        """A locked (or read-only) index must not stop the load, nor open the KB.

        The registry merge runs while every entry point is constructed and is
        documented not to raise. If the repair's write fails, the KB is still
        merged with the private policy -- in memory -- and the load goes on.
        """
        import sqlite3

        self._orphan(tmp_path, monkeypatch)
        config = load_config()
        blocker = sqlite3.connect(tmp_path / "index.db", timeout=0)
        blocker.execute("BEGIN EXCLUSIVE")
        try:
            db = PyriteDB(tmp_path / "index.db")
            try:
                db.merge_registered_kbs(config)  # must not raise
                assert config.get_kb("lost").default_role == "none"
                # The session is usable afterwards (rolled back, not poisoned).
                db.execute_sql("SELECT 1")
            finally:
                db.close()
        finally:
            blocker.rollback()
            blocker.close()

    # -- One owner of the decision -------------------------------------------
    #
    # The merge loop decides from the rows it loads: an orphaned ephemeral row
    # loads private whether or not anything else succeeds. Writing "none" back
    # to the row is best-effort record-keeping.

    @staticmethod
    def _fail_statements(monkeypatch, marker: str):
        """Make every ORM statement whose SQL contains `marker` fail.

        Only statements touching rows that have no policy carry the marker
        ("default_role IS NULL"); the merge's own SELECT does not, so it
        still succeeds -- a transient SQLITE_BUSY that hits one statement.
        """
        from sqlalchemy.exc import OperationalError
        from sqlalchemy.orm import Session

        from sqlalchemy import text as sql_text

        real = Session.execute

        def execute(self, statement, *args, **kwargs):
            if marker in str(statement):
                # As a real failing statement does: the session has begun its
                # transaction by the time the error arrives.
                real(self, sql_text("SELECT 1"))
                raise OperationalError(str(statement), {}, Exception("database is locked"))
            return real(self, statement, *args, **kwargs)

        monkeypatch.setattr(Session, "execute", execute)

    def test_kb_loads_private_when_every_policy_statement_fails(self, tmp_path, monkeypatch):
        """Acceptance 1: the statements that find or fix NULL policies fail;
        the merge's SELECT succeeds. The KB still loads "none"."""
        self._orphan(tmp_path, monkeypatch)
        config = load_config()
        self._fail_statements(monkeypatch, "default_role IS NULL")
        db = PyriteDB(tmp_path / "index.db")
        try:
            db.merge_registered_kbs(config)  # must not raise
            assert config.get_kb("lost").default_role == "none"
            assert config.get_kb("open-kb").default_role is None
            assert config.get_kb("root-kb").default_role is None
        finally:
            db.close()

    def test_a_failed_write_is_rolled_back(self, tmp_path, monkeypatch):
        """Acceptance 2 and 4: a write that fails under a lock is rolled back:
        the session holds no transaction afterwards, so a checkpoint by
        another connection is not blocked by it."""
        import sqlite3

        self._orphan(tmp_path, monkeypatch)
        config = load_config()
        db = PyriteDB(tmp_path / "index.db")
        blocker = sqlite3.connect(tmp_path / "index.db", timeout=0)
        blocker.execute("BEGIN EXCLUSIVE")
        try:
            db.merge_registered_kbs(config)  # must not raise
            assert config.get_kb("lost").default_role == "none"
            assert not db.session.in_transaction()
            blocker.rollback()
        finally:
            blocker.close()
            db.close()

    def test_a_second_merge_in_one_process_keeps_the_kb_private(self, tmp_path, monkeypatch):
        """Acceptance 3: seed_from_config merges again and the merge replaces
        the cached KB. With the write failing on both merges -- a lock on the
        first, a failing statement on the second -- the KB stays private."""
        import sqlite3

        self._orphan(tmp_path, monkeypatch)
        config = load_config()
        db = PyriteDB(tmp_path / "index.db")
        try:
            blocker = sqlite3.connect(tmp_path / "index.db", timeout=0)
            blocker.execute("BEGIN EXCLUSIVE")
            try:
                db.merge_registered_kbs(config)
            finally:
                blocker.rollback()
                blocker.close()
            assert config.get_kb("lost").default_role == "none"

            self._fail_statements(monkeypatch, "default_role IS NULL")
            db.merge_registered_kbs(config)
            assert config.get_kb("lost").default_role == "none"
        finally:
            db.close()

    def test_the_load_leaves_no_transaction_open(self, tmp_path, monkeypatch):
        """With nothing to record, the merge still ends its read transaction."""
        self._orphan(tmp_path, monkeypatch)
        config = load_config()
        db = PyriteDB(tmp_path / "index.db")
        try:
            db.merge_registered_kbs(config)  # records "none" for 'lost'
            db.merge_registered_kbs(config)  # nothing left to record
            assert config.get_kb("lost").default_role == "none"
            assert not db.session.in_transaction()
        finally:
            db.close()

    def test_a_failed_registry_read_is_rolled_back(self, tmp_path, monkeypatch):
        """The merge's own SELECT failing loads nothing, raises nothing, and
        leaves no failed transaction behind."""
        self._orphan(tmp_path, monkeypatch)
        config = load_config()
        db = PyriteDB(tmp_path / "index.db")
        try:
            self._fail_statements(monkeypatch, "FROM kb WHERE source = 'user'")
            assert db.merge_registered_kbs(config) == 0
            assert config.get_kb("lost") is None
            assert not db.session.in_transaction()
        finally:
            db.close()


@pytest.mark.parametrize("kind", ["unknown-user-home", "symlink-loop"])
def test_a_registry_path_that_cannot_be_resolved_loads_private(tmp_path, kind):
    """A row whose path cannot be resolved must not stop the load -- this runs
    while every entry point is constructed -- and fails closed: the KB is not
    loaded (unreachable, never open). Nothing is written back for it."""
    if kind == "unknown-user-home":
        path = "~nosuchuser_pyrite_zz/kb"
    else:
        loop = tmp_path / "loop"
        loop.symlink_to(loop)
        path = str(loop / "kb")
    config = PyriteConfig(
        knowledge_bases=[],
        settings=Settings(index_path=tmp_path / "index.db", workspace_path=tmp_path / "ws"),
    )
    db = PyriteDB(tmp_path / "index.db")
    try:
        db.register_kb("odd", "generic", path)
        db.merge_registered_kbs(config)  # must not raise
        assert config.get_kb("odd") is None
        row = db.execute_sql("SELECT default_role FROM kb WHERE name = 'odd'")
        assert row[0]["default_role"] is None
    finally:
        db.close()


def test_an_unresolvable_path_is_detected_on_every_python(tmp_path):
    """Python 3.13's non-strict ``resolve()`` returns a looping path instead of
    raising, which let such a KB load (dev CI on 3.13, 2026-09-25). The check
    resolves strictly, so it refuses a loop and an unknown ~user on every
    version, and accepts a path that only does not exist yet."""
    from pyrite.config import _refuse_unresolvable

    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    with pytest.raises((OSError, RuntimeError)):
        _refuse_unresolvable(loop / "kb")
    with pytest.raises(RuntimeError):
        _refuse_unresolvable(Path("~nosuchuser_pyrite_zz/kb"))
    _refuse_unresolvable(tmp_path / "not-yet" / "kb")  # missing is fine
    _refuse_unresolvable(tmp_path)  # existing is fine
