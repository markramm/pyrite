"""A repo-local `.pyrite/` config wins over `~/.pyrite` when no env var is set.

Under ADR-0032 every session works in its own worktree, but `pyrite -k pyrite`
resolved the KB through ~/.pyrite/config.yaml -- which registers the MAIN
checkout's kb/. Every worker's `pyrite update` on a ticket was silently
writing into the main checkout (2026-09-18, three stray modifications caught
by `git status`). A worktree needs its own config, found from where the
command runs: `./.pyrite/config.yaml`, searched upward from the cwd. An
explicit PYRITE_CONFIG_DIR / PYRITE_DATA_DIR still wins; tests that pin
CONFIG_DIR are unaffected because the local lookup only applies to the
default location.
"""

import os
from pathlib import Path

import pytest

import pyrite.config as config_module
from pyrite.config import resolve_config_dir


@pytest.fixture
def home_and_repo(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".pyrite").mkdir(parents=True)
    (home / ".pyrite" / "config.yaml").write_text("knowledge_bases: []\n")
    repo = tmp_path / "repo"
    (repo / ".pyrite").mkdir(parents=True)
    (repo / ".pyrite" / "config.yaml").write_text("knowledge_bases: []\n")
    (repo / "sub" / "dir").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("PYRITE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("PYRITE_DATA_DIR", raising=False)
    return home, repo


def test_local_dir_found_from_cwd_and_from_a_subdirectory(home_and_repo, monkeypatch):
    home, repo = home_and_repo
    monkeypatch.chdir(repo)
    assert resolve_config_dir() == (repo / ".pyrite").resolve()
    monkeypatch.chdir(repo / "sub" / "dir")
    assert resolve_config_dir() == (repo / ".pyrite").resolve()


def test_home_used_when_no_local_dir(home_and_repo, monkeypatch, tmp_path):
    home, _ = home_and_repo
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert resolve_config_dir() == (home / ".pyrite").resolve()


def test_env_var_wins_over_local_dir(home_and_repo, monkeypatch, tmp_path):
    _, repo = home_and_repo
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("PYRITE_CONFIG_DIR", str(explicit))
    monkeypatch.chdir(repo)
    assert resolve_config_dir() == explicit.resolve()


def test_local_dir_without_config_yaml_does_not_count(home_and_repo, monkeypatch):
    home, repo = home_and_repo
    (repo / ".pyrite" / "config.yaml").unlink()
    monkeypatch.chdir(repo)
    assert resolve_config_dir() == (home / ".pyrite").resolve()


def test_load_config_honours_the_local_dir(home_and_repo, monkeypatch):
    _, repo = home_and_repo
    (repo / "kb").mkdir()
    (repo / ".pyrite" / "config.yaml").write_text(
        f"knowledge_bases:\n- name: local\n  path: {repo / 'kb'}\n  kb_type: generic\n"
    )
    monkeypatch.chdir(repo)
    # The conftest isolation fixture pins CONFIG_DIR to a tmp dir; undo that here so
    # load_config exercises the real resolution (this test owns its own HOME).
    monkeypatch.setattr(config_module, "CONFIG_DIR", Path.home() / ".pyrite")
    monkeypatch.setattr(config_module, "CONFIG_FILE", Path.home() / ".pyrite" / "config.yaml")
    cfg = config_module.load_config()
    assert [kb.name for kb in cfg.knowledge_bases] == ["local"]
    assert os.path.samefile(cfg.knowledge_bases[0].path, repo / "kb")
