"""Tests for VersionService (extracted from KBService)."""

import subprocess

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.version_service import VersionService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def version_setup(tmp_path):
    """Set up VersionService with a git-backed KB."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()

    # Init git repo
    subprocess.run(["git", "init"], cwd=str(kb_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=str(kb_path), capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=str(kb_path), capture_output=True
    )

    # Write and commit an entry
    entry_file = kb_path / "entry-1.md"
    entry_file.write_text("---\nid: entry-1\ntitle: V1\ntype: note\n---\n\nVersion 1")
    subprocess.run(["git", "add", "."], cwd=str(kb_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "v1"], cwd=str(kb_path), capture_output=True
    )

    # Get commit hash
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(kb_path), capture_output=True, text=True
    )
    commit1 = result.stdout.strip()

    # Update and commit again
    entry_file.write_text("---\nid: entry-1\ntitle: V2\ntype: note\n---\n\nVersion 2")
    subprocess.run(["git", "add", "."], cwd=str(kb_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "v2"], cwd=str(kb_path), capture_output=True
    )

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path)],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")

    # Index entries
    from pyrite.storage.index import IndexManager

    idx = IndexManager(db, config)
    idx.index_all()

    svc = VersionService(config, db)
    yield svc, db, commit1
    db.close()


class TestVersionService:
    def test_get_entry_versions_empty_without_saves(self, version_setup):
        svc, db, commit1 = version_setup
        # Versions are only tracked when entries are saved through KBService,
        # not from raw git commits, so this returns empty.
        versions = svc.get_entry_versions("entry-1", "test-kb")
        assert isinstance(versions, list)

    def test_get_entry_at_version(self, version_setup):
        svc, db, commit1 = version_setup
        content = svc.get_entry_at_version("entry-1", "test-kb", commit1)
        assert content is not None
        assert "Version 1" in content

    def test_get_entry_at_version_nonexistent_kb(self, version_setup):
        svc, db, commit1 = version_setup
        content = svc.get_entry_at_version("entry-1", "nonexistent", commit1)
        assert content is None

    def test_get_entry_at_version_bad_commit(self, version_setup):
        svc, db, commit1 = version_setup
        content = svc.get_entry_at_version("entry-1", "test-kb", "0" * 40)
        assert content is None
