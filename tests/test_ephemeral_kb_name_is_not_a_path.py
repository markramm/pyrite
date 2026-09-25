"""An ephemeral KB's name must never become a path outside the ephemeral root.

`EphemeralKBService.create_ephemeral_kb` joined the caller-supplied name onto
`<workspace>/ephemeral/`, and `POST /api/kbs/ephemeral` lets any write-role
user supply that name. A name with `..` segments (or an absolute path) made
the "ephemeral" KB point at another KB's directory, with the caller granted
admin on it; after an index sync its private entries were readable under the
alias, and when the ephemeral KB expired, garbage collection removed the
directory it pointed at.

The name is now validated as a plain name before anything touches the disk,
a name already in use is refused, and expiry refuses to delete any directory
outside the ephemeral root (a KB persisted to config before this fix may
still point elsewhere).
"""

import os
import tempfile
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.services.auth_service import AuthService
from pyrite.services.ephemeral_service import EphemeralKBService, InvalidEphemeralKBNameError
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from tests.auth_seed import seed_and_sign_in

PRIVATE = "priv"
SECRET = "the source is Alice"

BAD_NAMES = [
    "../../priv",
    "../priv",
    "..",
    ".",
    "a/b",
    "a\\b",
    "/etc",
    "",
    " ",
    "-leading-dash",
    "x" * 65,
    "nul\x00byte",
]


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr("pyrite.config.CONFIG_FILE", tmp_path / "config.yaml")
    (tmp_path / PRIVATE).mkdir()
    (tmp_path / PRIVATE / "keep.md").write_text("---\ntitle: Keep\n---\nkeep")
    config = PyriteConfig(
        knowledge_bases=[
            KBConfig(name=PRIVATE, path=tmp_path / PRIVATE, kb_type="generic", default_role="none")
        ],
        settings=Settings(
            index_path=tmp_path / "index.db",
            workspace_path=tmp_path / "ws",
        ),
    )
    db = PyriteDB(config.settings.index_path)
    try:
        yield EphemeralKBService(config, db), config, tmp_path
    finally:
        db.close()


class TestServiceRejectsUnsafeNames:
    @pytest.mark.parametrize("name", BAD_NAMES)
    def test_unsafe_name_is_refused_before_touching_disk(self, svc, name):
        service, config, tmp = svc
        before = sorted(p.relative_to(tmp) for p in tmp.rglob("*"))

        with pytest.raises(ValueError):
            service.create_ephemeral_kb(name, ttl=3600)

        assert config.get_kb(name) is None
        assert [k.name for k in config.knowledge_bases] == [PRIVATE]
        after = sorted(p.relative_to(tmp) for p in tmp.rglob("*"))
        assert after == before

    def test_name_of_existing_kb_is_refused_before_touching_disk(self, svc):
        service, config, tmp = svc

        with pytest.raises(ValueError):
            service.create_ephemeral_kb(PRIVATE, ttl=3600)

        assert not (tmp / "ws" / "ephemeral" / PRIVATE).exists()
        assert config.get_kb(PRIVATE).ephemeral is False

    @pytest.mark.parametrize("name", ["scratch", "ephemeral-3-a1b2c3d4", "My_KB-2", "x" * 64])
    def test_plain_names_are_still_accepted(self, svc, name):
        service, config, tmp = svc
        kb = service.create_ephemeral_kb(name, ttl=3600)
        assert kb.path == tmp / "ws" / "ephemeral" / name
        assert kb.path.is_dir()


class TestExpiryNeverDeletesOutsideTheEphemeralRoot:
    """A KB persisted before the fix can still name another KB's directory."""

    def _planted(self, config, tmp, ttl):
        kb = KBConfig(
            name="../../priv",
            path=tmp / "ws" / "ephemeral" / ".." / ".." / PRIVATE,
            kb_type="generic",
            ephemeral=True,
            ttl=ttl,
            created_at_ts=time.time() - 100,
        )
        config.add_kb(kb)
        return kb

    def test_gc_leaves_a_directory_outside_the_root_alone(self, svc):
        service, config, tmp = svc
        self._planted(config, tmp, ttl=1)

        service.gc_ephemeral_kbs()

        assert (tmp / PRIVATE / "keep.md").exists()

    def test_force_expire_leaves_a_directory_outside_the_root_alone(self, svc):
        service, config, tmp = svc
        self._planted(config, tmp, ttl=3600)

        service.force_expire_kb("../../priv")

        assert (tmp / PRIVATE / "keep.md").exists()

    def test_gc_still_removes_a_real_ephemeral_directory(self, svc):
        service, config, tmp = svc
        kb = service.create_ephemeral_kb("short-lived", ttl=1)
        kb.created_at_ts = time.time() - 100

        assert service.gc_ephemeral_kbs() == ["short-lived"]
        assert not kb.path.exists()


@pytest.fixture
def server(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        monkeypatch.setattr("pyrite.config.CONFIG_FILE", tmp / "config.yaml")
        (tmp / PRIVATE).mkdir()
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name=PRIVATE, path=tmp / PRIVATE, kb_type="generic", default_role="none")
            ],
            settings=Settings(
                index_path=tmp / "index.db",
                workspace_path=tmp / "ws",
                auth=AuthConfig(enabled=True, allow_registration=True),
            ),
        )
        app = create_app(config=config)
        db = PyriteDB(config.settings.index_path)
        app.dependency_overrides[get_config] = lambda: config
        app.dependency_overrides[get_db] = lambda: db
        KBService(config, db).create_entry(
            PRIVATE, "source-identity", "Source identity", "note", SECRET
        )
        owner = TestClient(app)
        seed_and_sign_in(owner, "owner", "password123")  # the sole admin, via the operator path
        writer = TestClient(app)
        mallory = seed_and_sign_in(writer, "mallory", "password123")
        AuthService(db, config.settings.auth).set_role(mallory["id"], "write")
        try:
            yield {
                "tmp": tmp,
                "writer": writer,
                "writer_id": mallory["id"],
                "config": config,
                "db": db,
            }
        finally:
            db.close()


class TestEphemeralEndpoint:
    @pytest.mark.parametrize("name", ["../../priv", "../priv", "<abs>", PRIVATE])
    def test_write_user_cannot_alias_another_kb(self, server, name):
        writer, config, db = server["writer"], server["config"], server["db"]
        if name == "<abs>":
            name = str(server["tmp"] / PRIVATE)

        r = writer.post("/api/kbs/ephemeral", json={"name": name})

        assert r.status_code == 400, r.text
        assert [k.name for k in config.knowledge_bases] == [PRIVATE]
        grants = db.execute_sql(
            "SELECT kb_name FROM kb_permission WHERE user_id = :u", {"u": server["writer_id"]}
        )
        assert grants == []
        # A routine sync afterwards exposes nothing under any alias.
        IndexManager(db, config).sync_incremental()
        got = writer.get("/api/entries/source-identity", params={"kb": name})
        assert got.status_code == 404
        assert SECRET not in got.text

    def test_write_user_can_still_create_a_plainly_named_ephemeral_kb(self, server):
        r = server["writer"].post("/api/kbs/ephemeral", json={"name": "scratch"})
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "scratch"

    def test_write_user_can_still_create_an_unnamed_ephemeral_kb(self, server):
        r = server["writer"].post("/api/kbs/ephemeral", json={})
        assert r.status_code == 200, r.text
        assert r.json()["name"].startswith(f"ephemeral-{server['writer_id']}-")


class TestNameInUseOnEveryPath:
    """ "Already used by another KB" must hold beyond the in-memory config."""

    def test_name_registered_only_in_the_database_is_refused(self, svc):
        service, config, tmp = svc
        other = tmp / "db-only"
        other.mkdir()
        # A KB known to the registry table but absent from config and its
        # DB-KB cache (e.g. added by another process since this one loaded).
        service.db.register_kb(name="db-only", kb_type="generic", path=str(other))
        assert config.get_kb("db-only") is None

        with pytest.raises(InvalidEphemeralKBNameError):
            service.create_ephemeral_kb("db-only", ttl=3600)

        rows = service.db.execute_sql("SELECT path FROM kb WHERE name = 'db-only'")
        assert [r["path"] for r in rows] == [str(other)]
        assert not (tmp / "ws" / "ephemeral" / "db-only").exists()

    def test_row_registered_after_the_check_is_not_overwritten(self, svc, monkeypatch):
        # Another process registers the name between the in-use check and the
        # registration: the check saw nothing, and the row must survive.
        service, config, tmp = svc
        other = tmp / "late"
        other.mkdir()
        service.db.register_kb(name="late", kb_type="generic", path=str(other))
        real_execute_sql = service.db.execute_sql

        def check_sees_nothing(sql, params=None):
            if sql.lstrip().upper().startswith("SELECT 1 FROM KB"):
                return []
            return real_execute_sql(sql, params) if params is not None else real_execute_sql(sql)

        monkeypatch.setattr(service.db, "execute_sql", check_sees_nothing)

        with pytest.raises(InvalidEphemeralKBNameError):
            service.create_ephemeral_kb("late", ttl=3600)

        monkeypatch.undo()
        rows = service.db.execute_sql("SELECT path FROM kb WHERE name = 'late'")
        assert [r["path"] for r in rows] == [str(other)]
        assert config.get_kb("late") is None
        assert not (tmp / "ws" / "ephemeral" / "late").exists()

    def test_leftover_directory_is_not_reused(self, svc):
        service, config, tmp = svc
        leftover = tmp / "ws" / "ephemeral" / "leftover"
        leftover.mkdir(parents=True)
        (leftover / "old.md").write_text("someone else's")

        with pytest.raises(InvalidEphemeralKBNameError):
            service.create_ephemeral_kb("leftover", ttl=3600)

        assert config.get_kb("leftover") is None
        assert (leftover / "old.md").read_text() == "someone else's"

    def test_names_differing_only_by_case_never_share_a_directory(self, svc):
        # On a case-insensitive filesystem (macOS, Windows defaults) the two
        # names are one directory, so the second create must be refused. On a
        # case-sensitive one they are distinct directories and both may exist.
        service, config, tmp = svc
        first = service.create_ephemeral_kb("Scratch", ttl=3600)
        try:
            second = service.create_ephemeral_kb("scratch", ttl=3600)
        except InvalidEphemeralKBNameError:
            return
        assert not os.path.samefile(first.path, second.path)

    def test_concurrent_creates_of_one_name_admit_exactly_one(self, svc, monkeypatch):
        service, config, tmp = svc
        name = "contested"
        barrier = threading.Barrier(2, timeout=30)
        real_get_kb = config.get_kb

        def get_kb_then_wait(kb_name):
            result = real_get_kb(kb_name)
            if kb_name == name:
                # Both creates pass the in-use checks before either proceeds.
                barrier.wait()
            return result

        monkeypatch.setattr(config, "get_kb", get_kb_then_wait)
        outcomes: list = []

        def create():
            # Each caller has its own DB handle, as two requests or two server
            # processes would; the contested state is config and the disk.
            db = PyriteDB(config.settings.index_path)
            try:
                outcomes.append(EphemeralKBService(config, db).create_ephemeral_kb(name, ttl=3600))
            except Exception as e:
                outcomes.append(e)
            finally:
                db.close()

        threads = [threading.Thread(target=create) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        won = [o for o in outcomes if isinstance(o, KBConfig)]
        lost = [o for o in outcomes if not isinstance(o, KBConfig)]
        assert len(won) == 1, outcomes
        assert len(lost) == 1 and isinstance(lost[0], InvalidEphemeralKBNameError), outcomes
        assert [k.name for k in config.knowledge_bases].count(name) == 1
