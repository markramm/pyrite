"""A config save never drops a KB the caller did not name (#377).

The incident's writer replaced a config listing ~50 KBs with its own
in-memory config, which had never been loaded from that file, and every
command afterwards saw "No knowledge bases configured" for nine hours. The
first version of the guard only refused a write that left the registry
*empty*. A script that creates an ephemeral KB from a fresh config still
replaced the 50 with 1, and then expiring that KB (``removed=["ln"]``)
legitimately emptied it.

The rule now lives in one place, ``check_config_save`` (``save_config``
always runs it): every KB the file lists must be either in the config being
saved or named in ``removed=``. ``allow_drop=True`` is the explicit override.
Services that have destructive side effects (deleting a clone, unregistering
rows, removing an ephemeral directory) run the same check before those side
effects.
"""

import logging
import os
import time

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import pyrite.config as config_module
from pyrite.config import (
    ConfigFileUnreadableError,
    ConfigSaveRefusedError,
    KBConfig,
    PyriteConfig,
    Repository,
    Settings,
    check_config_save,
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


def _fresh_config(tmp_path, index="i.db") -> PyriteConfig:
    """A config built in memory -- never loaded from the file on disk."""
    return PyriteConfig(
        settings=Settings(index_path=tmp_path / index, workspace_path=tmp_path / "ws")
    )


REGISTRY_50 = [f"kb-{i:02d}" for i in range(50)]


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


class TestTheRule:
    def test_empty_config_over_a_registry_is_refused_and_the_file_is_untouched(
        self, cfg_dir, tmp_path
    ):
        before = _write_registry(cfg_dir, tmp_path, "alpha", "beta")

        with pytest.raises(ConfigSaveRefusedError) as exc:
            save_config(_fresh_config(tmp_path))

        msg = str(exc.value)
        assert str(cfg_dir / "config.yaml") in msg
        assert "allow_drop=True" in msg
        assert exc.value.dropped == ["alpha", "beta"]
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_partial_drop_is_refused(self, cfg_dir, tmp_path):
        """One KB over fifty is the create half of the incident."""
        before = _write_registry(cfg_dir, tmp_path, *REGISTRY_50)
        with pytest.raises(ConfigSaveRefusedError) as exc:
            save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "ln")]))
        assert exc.value.dropped == REGISTRY_50
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_adding_to_the_registry_is_fine(self, cfg_dir, tmp_path):
        _write_registry(cfg_dir, tmp_path, "alpha")
        save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "alpha"), _kb(tmp_path, "g")]))
        assert _names(cfg_dir) == ["alpha", "g"]

    def test_allow_drop_overrides(self, cfg_dir, tmp_path):
        _write_registry(cfg_dir, tmp_path, "alpha", "beta")
        save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "gamma")]), allow_drop=True)
        assert _names(cfg_dir) == ["gamma"]

    def test_removed_names_may_go(self, cfg_dir, tmp_path):
        _write_registry(cfg_dir, tmp_path, "alpha", "beta", "gamma")
        save_config(
            PyriteConfig(knowledge_bases=[_kb(tmp_path, "gamma")]), removed=["alpha", "beta"]
        )
        assert _names(cfg_dir) == ["gamma"]

    def test_removed_names_that_do_not_cover_the_drop_are_refused(self, cfg_dir, tmp_path):
        before = _write_registry(cfg_dir, tmp_path, "alpha", "beta")
        with pytest.raises(ConfigSaveRefusedError) as exc:
            save_config(PyriteConfig(), removed=["alpha"])
        assert exc.value.dropped == ["beta"]
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_removed_may_be_a_one_shot_iterable(self, cfg_dir, tmp_path):
        _write_registry(cfg_dir, tmp_path, "alpha", "beta")
        # Reverse order: a generator consumed by one membership test would
        # have nothing left for the next.
        save_config(PyriteConfig(), removed=(n for n in ["beta", "alpha"]))
        assert _names(cfg_dir) == []

    def test_removed_as_a_bare_string_is_a_type_error(self, cfg_dir, tmp_path):
        """ "ab" would otherwise mean the KBs named "a" and "b"."""
        before = _write_registry(cfg_dir, tmp_path, "a", "b")
        with pytest.raises(TypeError):
            save_config(PyriteConfig(), removed="ab")
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_empty_over_empty_and_over_nothing_are_fine(self, cfg_dir, tmp_path):
        save_config(PyriteConfig())  # no file yet
        assert _names(cfg_dir) == []
        save_config(PyriteConfig())  # empty over empty
        assert _names(cfg_dir) == []

    @pytest.mark.parametrize(
        "content",
        [
            "knowledge_bases: [\n  - name: broken\n",  # unparseable YAML
            "- just\n- a list\n",  # not a mapping
            "knowledge_bases: not-a-list\n",
            "knowledge_bases:\n- path: /no/name\n",  # an entry with no name
            # #405: from_dict reads kb_data["path"] and iterates the value of a
            # present knowledge_bases key, so none of these loads either.
            "knowledge_bases:\n- name: no-path\n",
            "knowledge_bases:\n- name: null-path\n  path: null\n",
            "knowledge_bases: null\n",
            "knowledge_bases: false\n",
        ],
    )
    def test_an_unreadable_file_is_refused_not_treated_as_empty(self, cfg_dir, tmp_path, content):
        (cfg_dir / "config.yaml").write_text(content)
        with pytest.raises(ConfigFileUnreadableError):
            save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "x")]))
        assert (cfg_dir / "config.yaml").read_text() == content

    @pytest.mark.control(reason="an empty file or an absent key already counts as no KBs")
    @pytest.mark.parametrize("content", ["", "settings: {}\n", "knowledge_bases: []\n"])
    def test_an_empty_file_or_an_absent_key_counts_as_no_kbs(self, cfg_dir, tmp_path, content):
        (cfg_dir / "config.yaml").write_text(content)
        save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "x")]))
        assert _names(cfg_dir) == ["x"]

    def test_allow_drop_may_replace_an_unreadable_file(self, cfg_dir, tmp_path):
        (cfg_dir / "config.yaml").write_text("knowledge_bases: [\n")
        save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "x")]), allow_drop=True)
        assert _names(cfg_dir) == ["x"]

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

        with pytest.raises(ConfigSaveRefusedError) as exc:
            save_config(PyriteConfig())
        assert str((real_dir / "config.yaml").resolve()) in str(exc.value)
        assert _names(real_dir) == ["alpha"]


# ---------------------------------------------------------------------------
# The incident's own shape
# ---------------------------------------------------------------------------


class TestIncidentShape:
    def test_create_then_expire_from_a_fresh_config_leaves_a_50_kb_registry_alone(
        self, cfg_dir, tmp_path
    ):
        """The coordinator's repro of #387: create from a fresh config wrote
        1 KB over 50; force-expire (removed=["ln"]) then wrote 0."""
        from pyrite.services.ephemeral_service import EphemeralKBService
        from pyrite.storage.database import PyriteDB

        before = _write_registry(cfg_dir, tmp_path, *REGISTRY_50)
        config = _fresh_config(tmp_path)
        db = PyriteDB(config.settings.index_path)
        try:
            svc = EphemeralKBService(config, db)
            with pytest.raises(ConfigSaveRefusedError):
                svc.create_ephemeral_kb("ln", ttl=1)
            # Refused before anything touched the disk or the index.
            assert not (tmp_path / "ws" / "ephemeral" / "ln").exists()
            assert db.execute_sql("SELECT name FROM kb WHERE name = 'ln'") == []
            assert config.get_kb("ln") is None

            # A KB planted in memory (as the probe did) and then expired.
            planted = tmp_path / "ws" / "ephemeral" / "planted"
            planted.mkdir(parents=True)
            (planted / "f").write_text("x")
            config.add_kb(
                KBConfig(
                    name="planted",
                    path=planted,
                    kb_type="generic",
                    ephemeral=True,
                    ttl=1,
                    created_at_ts=time.time() - 100,
                )
            )
            db.register_kb(name="planted", kb_type="generic", path=str(planted))
            with pytest.raises(ConfigSaveRefusedError):
                svc.force_expire_kb("planted")
            with pytest.raises(ConfigSaveRefusedError):
                svc.gc_ephemeral_kbs()
            # Nothing destructive happened before the refusal.
            assert (planted / "f").exists()
            assert db.execute_sql("SELECT name FROM kb WHERE name = 'planted'") != []
            assert config.get_kb("planted") is not None
        finally:
            db.close()
        assert (cfg_dir / "config.yaml").read_bytes() == before


# ---------------------------------------------------------------------------
# Every caller that legitimately removes KBs still can
# ---------------------------------------------------------------------------


class TestLegitimateCallers:
    def test_admin_kb_remove_of_the_last_kb(self, cfg_dir, tmp_path):
        from pyrite.admin_cli import app

        _write_registry(cfg_dir, tmp_path, "only")
        result = CliRunner().invoke(app, ["kb", "remove", "only"])
        assert result.exit_code == 0, result.output
        assert _names(cfg_dir) == []

    @pytest.mark.parametrize("cli", ["admin", "main"])
    def test_repo_remove_taking_its_kbs_with_it(self, cfg_dir, tmp_path, cli):
        if cli == "admin":
            from pyrite.admin_cli import app
        else:
            from pyrite.cli import app

        repo = Repository(name="r", path=tmp_path / "kbs")
        config = PyriteConfig(
            knowledge_bases=[
                _kb(tmp_path, "a", repo="r"),
                _kb(tmp_path, "b", repo="r"),
                _kb(tmp_path, "keep"),
            ],
            repositories=[repo],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        dump_yaml_file(config.to_dict(), cfg_dir / "config.yaml")

        result = CliRunner().invoke(app, ["repo", "remove", "r", "--force"])
        assert result.exit_code == 0, result.output
        assert _names(cfg_dir) == ["keep"]

    def _ephemeral(self, cfg_dir, tmp_path, ttl):
        from pyrite.services.ephemeral_service import EphemeralKBService
        from pyrite.storage.database import PyriteDB

        config = _fresh_config(tmp_path, index="index.db")
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

    def _subscribed(self, tmp_path):
        from pyrite.storage.database import PyriteDB

        db = PyriteDB(tmp_path / "index.db")
        clone = tmp_path / "kbs"
        repo_id = db.register_repo(name="owner/repo", local_path=str(clone))["id"]
        db.register_kb(name="sub-kb", kb_type="generic", path=str(clone / "sub-kb"))
        db.link_kb_to_repo("sub-kb", repo_id, "sub-kb")
        return db, clone

    def test_repo_service_unsubscribe_of_the_last_repo(self, cfg_dir, tmp_path):
        from pyrite.services.repo_service import RepoService

        _write_registry(cfg_dir, tmp_path, "sub-kb")
        config = load_config()
        db, _ = self._subscribed(tmp_path)
        try:
            result = RepoService(config, db).unsubscribe("owner/repo")
        finally:
            db.close()
        assert result["success"], result
        assert _names(cfg_dir) == []

    def test_unsubscribe_refuses_before_deleting_anything(self, cfg_dir, tmp_path):
        """Another process registered a KB after this config was loaded."""
        from pyrite.services.repo_service import RepoService

        _write_registry(cfg_dir, tmp_path, "sub-kb")
        config = load_config()
        before = _write_registry(cfg_dir, tmp_path, "sub-kb", "added-meanwhile")
        db, clone = self._subscribed(tmp_path)
        (clone / "sub-kb" / "entry.md").write_text("keep me")
        try:
            with pytest.raises(ConfigSaveRefusedError):
                RepoService(config, db).unsubscribe("owner/repo", delete_files=True)
            assert db.get_repo(name="owner/repo") is not None
            assert db.execute_sql("SELECT name FROM kb WHERE name = 'sub-kb'") != []
        finally:
            db.close()
        assert (clone / "sub-kb" / "entry.md").read_text() == "keep me"
        assert config.get_kb("sub-kb") is not None
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_check_config_save_is_the_same_rule_before_a_removal(self, cfg_dir, tmp_path):
        """Preflight: the KBs about to be removed are still in memory."""
        _write_registry(cfg_dir, tmp_path, "a", "b")
        config = load_config()
        check_config_save(config, removed=["a"])  # keeps b: fine
        config.remove_kb("b")  # dropped without saying so
        with pytest.raises(ConfigSaveRefusedError):
            check_config_save(config, removed=["a"])


# ---------------------------------------------------------------------------
# How a refusal reaches people
# ---------------------------------------------------------------------------


class TestRefusalSurfaces:
    def test_cli_prints_one_error_line_and_exits_1(self, cfg_dir, tmp_path, monkeypatch):
        import pyrite.admin_cli as admin_cli

        before = _write_registry(cfg_dir, tmp_path, "alpha")
        # A config that was never loaded from the file (a lost update, or the
        # incident's fresh config) reaches the save.
        monkeypatch.setattr(admin_cli, "load_config", lambda: PyriteConfig())
        new_kb = tmp_path / "new"
        new_kb.mkdir()

        result = CliRunner().invoke(admin_cli.app, ["kb", "add", str(new_kb), "--name", "n"])

        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "Traceback" not in result.output
        assert "alpha" in result.output
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_rest_returns_a_generic_409_and_logs_the_detail(self, cfg_dir, tmp_path, caplog):
        from pyrite.server.api import create_app, get_config, get_db
        from pyrite.storage.database import PyriteDB

        before = _write_registry(cfg_dir, tmp_path, "secret-registry-kb")
        config = _fresh_config(tmp_path, index="index.db")
        eph = tmp_path / "ws" / "ephemeral" / "scratch"
        eph.mkdir(parents=True)
        config.add_kb(
            KBConfig(
                name="scratch",
                path=eph,
                kb_type="generic",
                ephemeral=True,
                ttl=3600,
                created_at_ts=time.time(),
            )
        )
        app = create_app(config=config)
        db = PyriteDB(config.settings.index_path)
        app.dependency_overrides[get_config] = lambda: config
        app.dependency_overrides[get_db] = lambda: db
        try:
            with caplog.at_level(logging.WARNING):
                r = TestClient(app).delete("/api/kbs/ephemeral/scratch")
        finally:
            db.close()

        assert r.status_code == 409, r.text
        assert str(cfg_dir) not in r.text
        assert "secret-registry-kb" not in r.text
        assert any(str(cfg_dir) in rec.getMessage() for rec in caplog.records)
        assert eph.exists()
        assert (cfg_dir / "config.yaml").read_bytes() == before

    def test_main_cli_refusal_from_a_service_is_one_line_too(self, cfg_dir, tmp_path, monkeypatch):
        """The root group owns it: services called by commands raise too."""
        import pyrite.cli as main_cli

        before = _write_registry(cfg_dir, tmp_path, "alpha")
        stale = PyriteConfig(repositories=[Repository(name="r", path=tmp_path / "kbs")])
        monkeypatch.setattr(main_cli, "load_config", lambda: stale)

        result = CliRunner().invoke(main_cli.app, ["repo", "remove", "r", "--force"])

        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "CONFIG_SAVE_REFUSED" in result.output
        assert (cfg_dir / "config.yaml").read_bytes() == before


class TestRepoPreflight:
    """Subscribing and forking check the save before any remote or disk work."""

    @pytest.fixture
    def svc(self, cfg_dir, tmp_path, monkeypatch):
        from pyrite.services import repo_service as rs
        from pyrite.storage.database import PyriteDB

        self.before = _write_registry(cfg_dir, tmp_path, "alpha")
        self.calls = []

        def record(name):
            def fake(*a, **kw):
                self.calls.append(name)
                raise AssertionError(f"{name} ran before the config check")

            return fake

        monkeypatch.setattr(rs.GitService, "clone_with_code", staticmethod(record("clone")))
        monkeypatch.setattr(rs.GitService, "fork_repo", staticmethod(record("fork")))
        db = PyriteDB(tmp_path / "i.db")
        service = rs.RepoService(_fresh_config(tmp_path), db)
        monkeypatch.setattr(service, "_get_token", lambda: "token")
        yield service
        db.close()

    def test_subscribe(self, svc, cfg_dir, tmp_path):
        with pytest.raises(ConfigSaveRefusedError):
            svc.subscribe("https://github.com/owner/repo")
        assert self.calls == []
        assert not (tmp_path / "ws" / "owner").exists()
        assert (cfg_dir / "config.yaml").read_bytes() == self.before

    def test_fork_and_subscribe(self, svc, cfg_dir):
        with pytest.raises(ConfigSaveRefusedError):
            svc.fork_and_subscribe("https://github.com/owner/repo")
        assert self.calls == []
        assert (cfg_dir / "config.yaml").read_bytes() == self.before


# --- fix-at-review on 21bfc815 (delta cold read) ------------------------------


@pytest.mark.parametrize("raw_name", ["2024", "0", "true"])
def test_a_name_yaml_reads_as_a_number_or_bool_does_not_block_saves(cfg_dir, tmp_path, raw_name):
    """YAML reads `name: 2024` as an int (and `true` as a bool); the file side
    was compared as str and the in-memory side was not, so every save from a
    correctly loaded config was refused -- and `name: 0` counted as no name."""
    kb_dir = tmp_path / "kbs" / "odd"
    kb_dir.mkdir(parents=True)
    (cfg_dir / "config.yaml").write_text(
        f"knowledge_bases:\n- name: {raw_name}\n  path: {kb_dir}\n"
    )
    config = load_config()
    config.add_kb(_kb(tmp_path, "k2"))
    save_config(config)
    assert sorted(str(n) for n in _names(cfg_dir)) == sorted(
        [raw_name if raw_name != "true" else "True", "k2"]
    )


def test_removing_a_kb_whose_name_yaml_reads_as_a_number(cfg_dir, tmp_path):
    """The in-memory name is the int 2024; removed=[2024] must match the
    file's "2024" (both sides compared as str)."""
    kb_dir = tmp_path / "kbs" / "year"
    kb_dir.mkdir(parents=True)
    (cfg_dir / "config.yaml").write_text(f"knowledge_bases:\n- name: 2024\n  path: {kb_dir}\n")
    config = load_config()
    name = config.knowledge_bases[0].name
    assert name == 2024  # what YAML hands back
    config.remove_kb(name)
    save_config(config, removed=[name])
    assert _names(cfg_dir) == []


def test_a_refusal_tells_an_operator_to_restart_not_to_call_code(cfg_dir, tmp_path):
    _write_registry(cfg_dir, tmp_path, "a", "b")
    with pytest.raises(ConfigSaveRefusedError) as exc:
        save_config(_fresh_config(tmp_path))
    msg = str(exc.value)
    assert "Restart the server" in msg and "changed since this process loaded it" in msg
    assert "Restart the server" in ConfigSaveRefusedError.public_message


# --- fix round 3 (#387): the message follows the reason; the write is in place --


UNPARSEABLE = "knowledge_bases: [\n  - name: broken\n"


def _set_up_reason(reason, cfg_dir, tmp_path) -> bytes:
    """`dropped`: the file lists a KB this process does not know.
    `unreadable`: the file cannot be parsed, so nothing can be checked."""
    if reason == "dropped":
        return _write_registry(cfg_dir, tmp_path, "alpha")
    (cfg_dir / "config.yaml").write_text(UNPARSEABLE)
    return UNPARSEABLE.encode()


def _flat(text: str) -> str:
    """Rich wraps long lines at spaces; compare with the wrapping undone."""
    return " ".join(text.split()).lower()


def _assert_advice(reason, text):
    text = _flat(text)
    if reason == "dropped":
        assert "restart" in text and "re-run" in text, text
    else:
        # Restarting a server on an unparseable config.yaml fails at startup.
        assert "restart" not in text, text
        assert "fix or move" in text, text


@pytest.mark.parametrize("reason", ["dropped", "unreadable"])
def test_the_operator_message_follows_the_reason(cfg_dir, tmp_path, reason):
    _set_up_reason(reason, cfg_dir, tmp_path)
    with pytest.raises(ConfigSaveRefusedError) as exc:
        save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "x")]))
    _assert_advice(reason, str(exc.value))
    _assert_advice(reason, exc.value.public_message)
    assert str(cfg_dir) not in exc.value.public_message


@pytest.mark.parametrize("reason", ["dropped", "unreadable"])
def test_cli_refusal_advice_follows_the_reason(cfg_dir, tmp_path, monkeypatch, reason):
    import pyrite.admin_cli as admin_cli

    before = _set_up_reason(reason, cfg_dir, tmp_path)
    monkeypatch.setattr(admin_cli, "load_config", lambda: PyriteConfig())
    new_kb = tmp_path / "new"
    new_kb.mkdir()

    result = CliRunner().invoke(admin_cli.app, ["kb", "add", str(new_kb), "--name", "n"])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    _assert_advice(reason, result.output)
    assert (cfg_dir / "config.yaml").read_bytes() == before


@pytest.mark.parametrize("reason", ["dropped", "unreadable"])
def test_rest_refusal_advice_follows_the_reason(cfg_dir, tmp_path, caplog, reason):
    from pyrite.server.api import create_app, get_config, get_db
    from pyrite.storage.database import PyriteDB

    before = _set_up_reason(reason, cfg_dir, tmp_path)
    config = _fresh_config(tmp_path, index="index.db")
    eph = tmp_path / "ws" / "ephemeral" / "scratch"
    eph.mkdir(parents=True)
    config.add_kb(
        KBConfig(
            name="scratch",
            path=eph,
            kb_type="generic",
            ephemeral=True,
            ttl=3600,
            created_at_ts=time.time(),
        )
    )
    app = create_app(config=config)
    db = PyriteDB(config.settings.index_path)
    app.dependency_overrides[get_config] = lambda: config
    app.dependency_overrides[get_db] = lambda: db
    try:
        with caplog.at_level(logging.WARNING):
            r = TestClient(app).delete("/api/kbs/ephemeral/scratch")
    finally:
        db.close()

    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "CONFIG_SAVE_REFUSED"
    assert str(cfg_dir) not in r.text
    _assert_advice(reason, r.json()["detail"]["message"])
    assert any(str(cfg_dir) in rec.getMessage() for rec in caplog.records)
    assert eph.exists()
    assert (cfg_dir / "config.yaml").read_bytes() == before


def test_the_write_is_in_place_and_keeps_hard_links(cfg_dir, tmp_path):
    """A rename-over write gives config.yaml a new inode: a hard link to it
    keeps the old content, and so would any owner a root save does not keep."""
    _write_registry(cfg_dir, tmp_path, "a")
    alias = tmp_path / "alias.yaml"
    os.link(cfg_dir / "config.yaml", alias)
    config = load_config()
    config.add_kb(_kb(tmp_path, "b"))

    save_config(config)

    assert os.path.samefile(cfg_dir / "config.yaml", alias)
    assert "b" in [kb["name"] for kb in load_yaml_file(alias)["knowledge_bases"]]


def test_the_write_works_when_only_the_file_is_writable(cfg_dir, tmp_path):
    """A config dir the process cannot create files in (a read-only mount with
    one writable file, a root-owned ~/.pyrite) must not block a save."""
    _write_registry(cfg_dir, tmp_path, "a")
    config = load_config()
    config.add_kb(_kb(tmp_path, "b"))
    cfg_dir.chmod(0o555)
    try:
        save_config(config)
    finally:
        cfg_dir.chmod(0o755)
    assert _names(cfg_dir) == ["a", "b"]
