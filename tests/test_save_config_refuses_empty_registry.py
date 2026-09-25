"""save_config never silently empties a registry that lists KBs (#377).

The incident's write replaced a config listing ~50 KBs with one listing none,
through a symlinked ~/.pyrite/config.yaml; every command afterwards saw "No
knowledge bases configured" and said nothing for nine hours. That shape --
a file with KBs replaced by a file with none -- is never what a user wants
unless they just removed those KBs. save_config now refuses it unless the
caller says which KBs it removed (and they are all the file had) or passes
``allow_empty=True``.
"""

import logging
import time

import pytest
from typer.testing import CliRunner

import pyrite.config as config_module
from pyrite.config import (
    ConfigWouldEmptyRegistryError,
    KBConfig,
    PyriteConfig,
    Repository,
    Settings,
    load_config,
    save_config,
)
from pyrite.utils.yaml import dump_yaml_file, load_yaml_file


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    monkeypatch.setattr(config_module, "CONFIG_DIR", d)
    monkeypatch.setattr(config_module, "CONFIG_FILE", d / "config.yaml")
    monkeypatch.delenv("PYRITE_DATA_DIR", raising=False)
    return d


def _kb(tmp_path, name, **kw) -> KBConfig:
    path = tmp_path / "kbs" / name
    path.mkdir(parents=True, exist_ok=True)
    return KBConfig(name=name, path=path, kb_type="generic", **kw)


def _write_registry(cfg_dir, tmp_path, *names, repos=()) -> bytes:
    config = PyriteConfig(
        knowledge_bases=[_kb(tmp_path, n) for n in names],
        repositories=list(repos),
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    dump_yaml_file(config.to_dict(), cfg_dir / "config.yaml")
    return (cfg_dir / "config.yaml").read_bytes()


def _names(cfg_dir) -> list[str]:
    data = load_yaml_file(cfg_dir / "config.yaml") or {}
    return [kb["name"] for kb in data.get("knowledge_bases") or []]


class TestTheGuard:
    def test_incident_shape_is_refused_and_the_file_is_untouched(self, cfg_dir, tmp_path):
        before = _write_registry(cfg_dir, tmp_path, "alpha", "beta")
        fixture_shaped = PyriteConfig(settings=Settings(index_path=tmp_path / "t" / "i.db"))

        with pytest.raises(ConfigWouldEmptyRegistryError) as exc:
            save_config(fixture_shaped)

        msg = str(exc.value)
        assert str(cfg_dir / "config.yaml") in msg
        assert "allow_empty=True" in msg
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_allow_empty_overrides(self, cfg_dir, tmp_path):
        _write_registry(cfg_dir, tmp_path, "alpha")
        save_config(PyriteConfig(), allow_empty=True)
        assert _names(cfg_dir) == []

    def test_removing_exactly_what_the_file_lists_is_allowed(self, cfg_dir, tmp_path):
        _write_registry(cfg_dir, tmp_path, "alpha", "beta")
        save_config(PyriteConfig(), removed=["alpha", "beta"])
        assert _names(cfg_dir) == []

    def test_removed_names_that_do_not_cover_the_file_are_refused(self, cfg_dir, tmp_path):
        """An ephemeral GC in a script whose in-memory config never saw the
        real registry removes *its* KB -- not the fifty in the file."""
        before = _write_registry(cfg_dir, tmp_path, "alpha", "beta")
        with pytest.raises(ConfigWouldEmptyRegistryError):
            save_config(PyriteConfig(), removed=["alpha"])
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_empty_over_empty_and_over_nothing_are_fine(self, cfg_dir, tmp_path):
        save_config(PyriteConfig())  # no file yet
        assert _names(cfg_dir) == []
        save_config(PyriteConfig())  # empty over empty
        assert _names(cfg_dir) == []

    def test_non_empty_writes_are_unaffected(self, cfg_dir, tmp_path):
        _write_registry(cfg_dir, tmp_path, "alpha", "beta")
        save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "gamma")]))
        assert _names(cfg_dir) == ["gamma"]

    def test_write_through_a_symlink_logs_the_real_path(self, cfg_dir, tmp_path, caplog):
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        real = real_dir / "config.yaml"
        real.write_text("knowledge_bases: []\n")
        (cfg_dir / "config.yaml").symlink_to(real)

        with caplog.at_level(logging.WARNING, logger="pyrite.config"):
            save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "alpha")]))

        assert (cfg_dir / "config.yaml").is_symlink()
        assert "alpha" in real.read_text()
        assert any(str(real.resolve()) in r.getMessage() for r in caplog.records)

    def test_refusal_through_a_symlink_names_the_real_file(self, cfg_dir, tmp_path):
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        _write_registry(real_dir, tmp_path, "alpha")
        (cfg_dir / "config.yaml").symlink_to(real_dir / "config.yaml")

        with pytest.raises(ConfigWouldEmptyRegistryError) as exc:
            save_config(PyriteConfig())
        assert str((real_dir / "config.yaml").resolve()) in str(exc.value)
        assert _names(real_dir) == ["alpha"]


# ---------------------------------------------------------------------------
# Every caller that legitimately removes the last KB still can
# ---------------------------------------------------------------------------


class TestLegitimateCallersStillEmpty:
    def test_admin_kb_remove_of_the_last_kb(self, cfg_dir, tmp_path):
        from pyrite.admin_cli import app

        _write_registry(cfg_dir, tmp_path, "only")
        result = CliRunner().invoke(app, ["kb", "remove", "only"])
        assert result.exit_code == 0, result.output
        assert _names(cfg_dir) == []

    @pytest.mark.parametrize("cli", ["admin", "main"])
    def test_repo_remove_taking_the_last_kbs_with_it(self, cfg_dir, tmp_path, cli):
        if cli == "admin":
            from pyrite.admin_cli import app
        else:
            from pyrite.cli import app

        repo = Repository(name="r", path=tmp_path / "kbs")
        config = PyriteConfig(
            knowledge_bases=[_kb(tmp_path, "a", repo="r"), _kb(tmp_path, "b", repo="r")],
            repositories=[repo],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        dump_yaml_file(config.to_dict(), cfg_dir / "config.yaml")

        result = CliRunner().invoke(app, ["repo", "remove", "r", "--force"])
        assert result.exit_code == 0, result.output
        assert _names(cfg_dir) == []

    def _ephemeral(self, cfg_dir, tmp_path, ttl):
        from pyrite.services.ephemeral_service import EphemeralKBService
        from pyrite.storage.database import PyriteDB

        config = PyriteConfig(
            settings=Settings(index_path=tmp_path / "index.db", workspace_path=tmp_path / "ws")
        )
        db = PyriteDB(config.settings.index_path)
        svc = EphemeralKBService(config, db)
        kb = svc.create_ephemeral_kb("scratch", ttl=ttl)
        kb.created_at_ts = time.time() - 100
        assert _names(cfg_dir) == ["scratch"]
        return svc, db

    def test_ephemeral_gc_of_the_last_kb(self, cfg_dir, tmp_path):
        svc, db = self._ephemeral(cfg_dir, tmp_path, ttl=1)
        try:
            assert svc.gc_ephemeral_kbs() == ["scratch"]
        finally:
            db.close()
        assert _names(cfg_dir) == []

    def test_ephemeral_force_expire_of_the_last_kb(self, cfg_dir, tmp_path):
        svc, db = self._ephemeral(cfg_dir, tmp_path, ttl=3600)
        try:
            assert svc.force_expire_kb("scratch") is True
        finally:
            db.close()
        assert _names(cfg_dir) == []

    def test_ephemeral_gc_in_a_script_cannot_empty_a_registry_it_never_loaded(
        self, cfg_dir, tmp_path
    ):
        """The likely incident: a script builds its own config, creates and
        expires an ephemeral KB, and saves -- over a real registry."""
        from pyrite.services.ephemeral_service import EphemeralKBService
        from pyrite.storage.database import PyriteDB

        config = PyriteConfig(
            settings=Settings(index_path=tmp_path / "i.db", workspace_path=tmp_path / "ws")
        )
        db = PyriteDB(config.settings.index_path)
        try:
            svc = EphemeralKBService(config, db)
            kb = svc.create_ephemeral_kb("scratch", ttl=1)
            kb.created_at_ts = time.time() - 100
            # Meanwhile the file on disk is the user's registry.
            _write_registry(cfg_dir, tmp_path, "precious-1", "precious-2")
            with pytest.raises(ConfigWouldEmptyRegistryError):
                svc.gc_ephemeral_kbs()
        finally:
            db.close()
        assert _names(cfg_dir) == ["precious-1", "precious-2"]

    def test_repo_service_unsubscribe_of_the_last_repo(self, cfg_dir, tmp_path):
        from pyrite.services.repo_service import RepoService
        from pyrite.storage.database import PyriteDB

        _write_registry(cfg_dir, tmp_path, "sub-kb")
        config = load_config()
        db = PyriteDB(tmp_path / "index.db")
        try:
            repo_id = db.register_repo(name="owner/repo", local_path=str(tmp_path / "kbs"))["id"]
            db.register_kb(name="sub-kb", kb_type="generic", path=str(tmp_path / "kbs" / "sub-kb"))
            db.link_kb_to_repo("sub-kb", repo_id, "sub-kb")
            result = RepoService(config, db).unsubscribe("owner/repo")
        finally:
            db.close()
        assert result["success"], result
        assert _names(cfg_dir) == []
