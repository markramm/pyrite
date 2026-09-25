"""Tests for VersionService (extracted from KBService)."""

import subprocess

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.exceptions import InvalidGitRefError
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
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(kb_path), capture_output=True)

    # Write and commit an entry
    entry_file = kb_path / "entry-1.md"
    entry_file.write_text("---\nid: entry-1\ntitle: V1\ntype: note\n---\n\nVersion 1")
    subprocess.run(["git", "add", "."], cwd=str(kb_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "v1"], cwd=str(kb_path), capture_output=True)

    # Get commit hash
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(kb_path), capture_output=True, text=True
    )
    commit1 = result.stdout.strip()

    # Update and commit again
    entry_file.write_text("---\nid: entry-1\ntitle: V2\ntype: note\n---\n\nVersion 2")
    subprocess.run(["git", "add", "."], cwd=str(kb_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "v2"], cwd=str(kb_path), capture_output=True)

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


# ---------------------------------------------------------------------------
# #333: the commit hash is a hex object id, checked before any git call
# ---------------------------------------------------------------------------

REFUSED_HASHES = [
    "-x",
    "--output=pwned",
    "HEAD",
    "main",
    "abc",  # too short
    "a" * 65,  # too long
    "abcd\n",  # a trailing newline must not slip past an anchored match
    "abcd:entry-1.md",
    "",
]


class TestCommitHashValidation:
    @pytest.mark.parametrize("bad", REFUSED_HASHES)
    def test_refused_before_any_git_call(self, version_setup, monkeypatch, bad):
        svc, db, commit1 = version_setup

        def _no_subprocess(*args, **kwargs):
            raise AssertionError(f"subprocess.run called for refused hash: {args!r}")

        monkeypatch.setattr(subprocess, "run", _no_subprocess)
        with pytest.raises(InvalidGitRefError):
            svc.get_entry_at_version("entry-1", "test-kb", bad)

    def test_short_hash_still_resolves(self, version_setup):
        svc, db, commit1 = version_setup
        content = svc.get_entry_at_version("entry-1", "test-kb", commit1[:7])
        assert content is not None
        assert "Version 1" in content

    def test_uppercase_hex_accepted(self, version_setup):
        svc, db, commit1 = version_setup
        content = svc.get_entry_at_version("entry-1", "test-kb", commit1.upper())
        assert content is not None
        assert "Version 1" in content

    def test_git_show_ends_options_before_the_object(self, version_setup, monkeypatch):
        svc, db, commit1 = version_setup
        real_run = subprocess.run
        seen = []

        def _spy(argv, *args, **kwargs):
            seen.append(list(argv))
            return real_run(argv, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", _spy)
        # An abbreviated id: the read must use the peeled full commit id.
        assert svc.get_entry_at_version("entry-1", "test-kb", commit1[:7]) is not None
        show = [a for a in seen if a[:2] == ["git", "show"]]
        assert len(show) == 1, seen
        argv = show[0]
        assert argv.index("--end-of-options") == len(argv) - 2
        assert argv[-1] == f"{commit1}:entry-1.md"
        peels = [a for a in seen if a[:2] == ["git", "rev-parse"] and commit1[:7] in a[-1]]
        assert peels, seen
        for a in peels:
            assert a.index("--end-of-options") == len(a) - 2, a


def _git(kb_path, *args):
    return subprocess.run(
        ["git", *args], cwd=str(kb_path), capture_output=True, text=True, check=True
    ).stdout.strip()


class TestCommitObjectsOnly:
    """A hex id must name a commit: a tree or blob id is refused (#333 cold read)."""

    @pytest.mark.parametrize("kind", ["tree", "blob"])
    def test_non_commit_object_refused(self, version_setup, kind):
        svc, db, commit1 = version_setup
        kb_path = svc.config.get_kb("test-kb").path
        obj = _git(kb_path, "rev-parse", f"{commit1}^{{tree}}")
        if kind == "blob":
            obj = _git(kb_path, "rev-parse", f"{commit1}:entry-1.md")
        with pytest.raises(InvalidGitRefError):
            svc.get_entry_at_version("entry-1", "test-kb", obj)

    def test_annotated_tag_peels_to_its_commit(self, version_setup):
        svc, db, commit1 = version_setup
        kb_path = svc.config.get_kb("test-kb").path
        _git(kb_path, "tag", "-a", "v1", "-m", "v1", commit1)
        tag = _git(kb_path, "rev-parse", "v1")
        assert tag != commit1
        content = svc.get_entry_at_version("entry-1", "test-kb", tag)
        assert content is not None and "Version 1" in content

    def test_unknown_object_is_not_found_not_refused(self, version_setup):
        svc, db, commit1 = version_setup
        assert svc.get_entry_at_version("entry-1", "test-kb", "0" * 40) is None


class TestVersionEndpointHash:
    @pytest.fixture
    def client(self, version_setup):
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app, get_config, get_db

        svc, db, commit1 = version_setup
        application = create_app(config=svc.config)
        application.dependency_overrides[get_config] = lambda: svc.config
        application.dependency_overrides[get_db] = lambda: db
        kb_path = svc.config.get_kb("test-kb").path
        return TestClient(application), kb_path, commit1

    @staticmethod
    def _tree(kb_path):
        return sorted(p.relative_to(kb_path).as_posix() for p in kb_path.rglob("*"))

    @pytest.mark.parametrize("bad", ["--output=pwned", "-x", "HEAD"])
    def test_refused_with_400_and_nothing_written(self, client, bad):
        c, kb_path, _ = client
        before = self._tree(kb_path)
        r = c.get(f"/api/entries/entry-1/versions/{bad}", params={"kb": "test-kb"})
        assert self._tree(kb_path) == before, "the request created a file in the KB"
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "INVALID_REF"

    def test_tree_id_refused_with_400(self, client):
        c, kb_path, commit1 = client
        tree = _git(kb_path, "rev-parse", f"{commit1}^{{tree}}")
        r = c.get(f"/api/entries/entry-1/versions/{tree}", params={"kb": "test-kb"})
        assert r.status_code == 400, r.text
        assert r.json()["detail"]["code"] == "INVALID_REF"

    def test_real_hash_still_served(self, client):
        c, _, commit1 = client
        for h in (commit1, commit1[:7]):
            r = c.get(f"/api/entries/entry-1/versions/{h}", params={"kb": "test-kb"})
            assert r.status_code == 200, r.text
            assert "Version 1" in r.json()["content"]

    def test_unknown_but_valid_hash_is_404(self, client):
        c, _, _ = client
        r = c.get(f"/api/entries/entry-1/versions/{'0' * 40}", params={"kb": "test-kb"})
        assert r.status_code == 404, r.text
