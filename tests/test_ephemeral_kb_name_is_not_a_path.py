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

import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.services.auth_service import AuthService
from pyrite.services.ephemeral_service import EphemeralKBService
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager

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
        assert (
            owner.post(
                "/auth/register", json={"username": "owner", "password": "password123"}
            ).status_code
            == 200
        )
        writer = TestClient(app)
        r = writer.post("/auth/register", json={"username": "mallory", "password": "password123"})
        assert r.status_code == 200, r.text
        AuthService(db, config.settings.auth).set_role(r.json()["id"], "write")
        try:
            yield {
                "tmp": tmp,
                "writer": writer,
                "writer_id": r.json()["id"],
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
