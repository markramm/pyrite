"""Default-path writes stay inside the configured directory (#377).

On 2026-09-23 something shaped like a test fixture -- ``knowledge_bases: []``,
``index_path`` in a ``tempfile.TemporaryDirectory`` -- overwrote a user's
global ``~/.pyrite/config.yaml`` (a symlink to a ~50-KB production registry)
and nobody noticed for nine hours. Two defaults let it happen:

1. The suite isolated the config only *in-process* (``tests/conftest.py``
   monkeypatches ``CONFIG_DIR``). A ``pyrite`` / ``pyrite-admin`` / ``python
   -c`` child process does not inherit a monkeypatch, so it read and wrote the
   real ``~/.pyrite``. The repo-root ``conftest.py`` now exports
   ``PYRITE_CONFIG_DIR`` for the whole session and clears ``PYRITE_DATA_DIR``
   (which would override every explicit ``settings.index_path`` in-process and
   win over ``PYRITE_CONFIG_DIR`` when resolving the config dir).
2. ``PYRITE_CONFIG_DIR`` moved the config file but not the index:
   ``Settings.index_path`` defaulted to ``~/.pyrite/index.db`` regardless, so a
   sandboxed ``pyrite kb add`` still registered into the user's real index.

These tests run real subprocesses with a fake ``HOME`` and look at the files.
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pyrite.config as config_module
from pyrite.config import PyriteConfig, Settings

BIN = Path(sys.executable).parent
TIMEOUT = 120


def _run(args: list[str], *, env: dict, cwd: Path) -> subprocess.CompletedProcess:
    proc = subprocess.run(args, env=env, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
    assert proc.returncode == 0, f"{args} failed:\n{proc.stdout}\n{proc.stderr}"
    return proc


def _kb_names(index_db: Path) -> set[str]:
    conn = sqlite3.connect(index_db)
    try:
        return {row[0] for row in conn.execute("SELECT name FROM kb")}
    finally:
        conn.close()


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Every file under root with its size and mtime -- 'untouched' means equal."""
    if not root.exists():
        return {}
    return {
        str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# (1) The session is isolated, and child processes inherit it
# ---------------------------------------------------------------------------


class TestSessionIsolation:
    def test_session_exports_a_config_dir_outside_home(self):
        home_pyrite = (Path.home() / ".pyrite").resolve()
        tmp_root = Path(tempfile.gettempdir()).resolve()
        value = os.environ.get("PYRITE_CONFIG_DIR")
        assert value, "PYRITE_CONFIG_DIR is not set for the test session"
        resolved = Path(value).resolve()
        assert resolved.is_relative_to(tmp_root), f"PYRITE_CONFIG_DIR={value} is not a temp dir"
        assert not resolved.is_relative_to(home_pyrite), (
            f"PYRITE_CONFIG_DIR={value} is under ~/.pyrite"
        )

    def test_session_does_not_export_a_data_dir(self, tmp_path):
        """PYRITE_DATA_DIR would override an explicit settings.index_path in
        every in-process load_config -- and hide precedence bugs."""
        assert "PYRITE_DATA_DIR" not in os.environ
        explicit = tmp_path / "explicit.db"
        cfg = Path(os.environ["PYRITE_CONFIG_DIR"])
        probe = "import pyrite.config as c\nprint(c.load_config().settings.index_path)\n"
        env = dict(os.environ)
        env["HOME"] = str(tmp_path / "home")
        own = tmp_path / "own-cfg"
        own.mkdir()
        (own / "config.yaml").write_text(f"settings:\n  index_path: {explicit}\n")
        env["PYRITE_CONFIG_DIR"] = str(own)
        out = _run([sys.executable, "-c", probe], env=env, cwd=tmp_path).stdout.strip()
        assert Path(out) == explicit.resolve()
        assert cfg.exists()

    def test_child_process_writes_nothing_under_home(self, tmp_path):
        """A config write and an index write from `pyrite-admin` / `pyrite`,
        spawned the way ~20 test files spawn them (inheriting the environment),
        leave a HOME-derived ~/.pyrite exactly as it was."""
        home = tmp_path / "home"
        (home / ".pyrite").mkdir(parents=True)
        sentinel = home / ".pyrite" / "config.yaml"
        sentinel.write_text("knowledge_bases:\n- name: precious\n  path: /nowhere\n")
        before = _snapshot(home)
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        name = f"iso-{uuid.uuid4().hex[:8]}"

        env = dict(os.environ)
        env["HOME"] = str(home)
        _run(
            [str(BIN / "pyrite-admin"), "kb", "add", str(kb_dir), "--name", name],
            env=env,
            cwd=tmp_path,
        )
        _run(
            [str(BIN / "pyrite"), "kb", "add", str(kb_dir), "--name", f"{name}-idx"],
            env=env,
            cwd=tmp_path,
        )
        listed = _run([str(BIN / "pyrite"), "kb", "list"], env=env, cwd=tmp_path)
        try:
            assert _snapshot(home) == before
            assert "precious" not in listed.stdout
            session = Path(os.environ["PYRITE_CONFIG_DIR"])
            assert name in (session / "config.yaml").read_text()
        finally:
            subprocess.run(
                [str(BIN / "pyrite"), "kb", "remove", f"{name}-idx", "--force"],
                env=env,
                cwd=tmp_path,
                capture_output=True,
                timeout=TIMEOUT,
            )
            subprocess.run(
                [str(BIN / "pyrite-admin"), "kb", "remove", name],
                env=env,
                cwd=tmp_path,
                capture_output=True,
                timeout=TIMEOUT,
            )

    def test_child_python_resolves_every_default_into_the_session_dir(self, tmp_path):
        """`python -c` scripts that build a config and save it (the incident's
        likely shape) resolve CONFIG_FILE, index and workspace under the session dir."""
        env = dict(os.environ)
        env["HOME"] = str(tmp_path / "home")
        probe = (
            "import pyrite.config as c\n"
            "cfg = c.load_config()\n"
            "print(c.current_config_file())\n"
            "print(cfg.settings.index_path)\n"
            "print(cfg.settings.workspace_path)\n"
        )
        out = _run([sys.executable, "-c", probe], env=env, cwd=tmp_path).stdout.split()
        session = Path(os.environ["PYRITE_CONFIG_DIR"]).resolve()
        for line in out:
            assert Path(line).resolve().is_relative_to(session), out


# ---------------------------------------------------------------------------
# (2) The index follows the config dir
# ---------------------------------------------------------------------------


def _sandbox_env(tmp_path: Path, *, config_dir: Path | None, data_dir: Path | None) -> dict:
    env = dict(os.environ)
    env.pop("PYRITE_CONFIG_DIR", None)
    env.pop("PYRITE_DATA_DIR", None)
    env["HOME"] = str(tmp_path / "home")
    (tmp_path / "home").mkdir(exist_ok=True)
    if config_dir is not None:
        env["PYRITE_CONFIG_DIR"] = str(config_dir)
    if data_dir is not None:
        env["PYRITE_DATA_DIR"] = str(data_dir)
    return env


class TestIndexFollowsConfigDir:
    def test_kb_add_with_config_dir_registers_in_that_dirs_index(self, tmp_path):
        """The issue's repro: PYRITE_CONFIG_DIR alone, `pyrite kb add`."""
        cfg, kb = tmp_path / "cfg", tmp_path / "kb"
        cfg.mkdir()
        kb.mkdir()
        env = _sandbox_env(tmp_path, config_dir=cfg, data_dir=None)

        _run(
            [str(BIN / "pyrite"), "kb", "add", str(kb), "--name", "repro", "--type", "generic"],
            env=env,
            cwd=tmp_path,
        )

        assert not (tmp_path / "home" / ".pyrite" / "index.db").exists()
        assert "repro" in _kb_names(cfg / "index.db")

    def test_default_dir_users_see_no_change(self, tmp_path):
        """No env var, no repo-local config: ~/.pyrite/index.db, as before."""
        kb = tmp_path / "kb"
        kb.mkdir()
        env = _sandbox_env(tmp_path, config_dir=None, data_dir=None)

        _run([str(BIN / "pyrite"), "kb", "add", str(kb), "--name", "plain"], env=env, cwd=tmp_path)

        assert "plain" in _kb_names(tmp_path / "home" / ".pyrite" / "index.db")

    def test_data_dir_wins_over_config_dir(self, tmp_path):
        cfg, data, kb = tmp_path / "cfg", tmp_path / "data", tmp_path / "kb"
        for d in (cfg, data, kb):
            d.mkdir()
        env = _sandbox_env(tmp_path, config_dir=cfg, data_dir=data)

        _run([str(BIN / "pyrite"), "kb", "add", str(kb), "--name", "both"], env=env, cwd=tmp_path)

        assert "both" in _kb_names(data / "index.db")
        assert not (cfg / "index.db").exists()

    def test_explicit_index_path_in_config_beats_the_config_dir_default(self, tmp_path):
        cfg, kb = tmp_path / "cfg", tmp_path / "kb"
        cfg.mkdir()
        kb.mkdir()
        explicit = tmp_path / "elsewhere" / "idx.db"
        (cfg / "config.yaml").write_text(f"settings:\n  index_path: {explicit}\n")
        env = _sandbox_env(tmp_path, config_dir=cfg, data_dir=None)

        _run([str(BIN / "pyrite"), "kb", "add", str(kb), "--name", "pinned"], env=env, cwd=tmp_path)

        assert "pinned" in _kb_names(explicit)
        assert not (cfg / "index.db").exists()

    def test_in_process_defaults_follow_the_pinned_config_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PYRITE_DATA_DIR", raising=False)
        monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.yaml")

        for settings in (Settings(), PyriteConfig.from_dict({}).settings):
            assert settings.index_path == tmp_path.resolve() / "index.db"
            assert settings.workspace_path == tmp_path.resolve() / "repos"
