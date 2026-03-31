"""Tests for WorktreeService: per-user git worktree management."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from pyrite.services.git_service import GitService
from pyrite.services.worktree_service import WorktreeInfo, WorktreeService
from pyrite.storage.database import PyriteDB


def _init_git_repo(path: Path) -> None:
    """Initialize a git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    # Create initial commit
    (path / "README.md").write_text("# Test KB\n")
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )


def _make_config(kb_path: Path, kb_name: str = "test"):
    """Create a minimal PyriteConfig with one KB."""
    from pyrite.config import KBConfig, PyriteConfig, Settings

    kb = KBConfig(name=kb_name, path=kb_path, kb_type="generic")
    return PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=Path(tempfile.mkdtemp()) / "index.db"),
    )


class TestGitServiceWorktree:
    """Test GitService worktree static methods against a real git repo."""

    def test_worktree_add_creates_directory(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        wt_path = tmp_path / "worktrees" / "alice"
        success, msg = GitService.worktree_add(repo, wt_path, "user/alice")

        assert success, msg
        assert wt_path.exists()
        assert (wt_path / "README.md").exists()

    def test_worktree_add_idempotent_existing_branch(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        wt1 = tmp_path / "wt1"
        success, _ = GitService.worktree_add(repo, wt1, "user/alice")
        assert success

        # Remove worktree but keep branch
        GitService.worktree_remove(repo, wt1, force=True)

        # Re-add with same branch name
        wt2 = tmp_path / "wt2"
        success, msg = GitService.worktree_add(repo, wt2, "user/alice")
        assert success, msg

    def test_worktree_list(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        GitService.worktree_add(repo, tmp_path / "wt-a", "user/alice")
        GitService.worktree_add(repo, tmp_path / "wt-b", "user/bob")

        worktrees = GitService.worktree_list(repo)
        # Main repo + 2 worktrees
        assert len(worktrees) >= 3
        branches = [wt.get("branch", "") for wt in worktrees]
        assert any("user/alice" in b for b in branches)
        assert any("user/bob" in b for b in branches)

    def test_worktree_remove(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        wt_path = tmp_path / "wt-remove"
        GitService.worktree_add(repo, wt_path, "user/temp")

        success, msg = GitService.worktree_remove(repo, wt_path)
        assert success, msg
        assert not wt_path.exists()

    def test_merge_branch_success(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        # Create a branch with a change
        wt_path = tmp_path / "wt-merge"
        GitService.worktree_add(repo, wt_path, "user/alice")
        (wt_path / "alice.md").write_text("# Alice's entry\n")
        subprocess.run(["git", "add", "."], cwd=str(wt_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Alice's change"],
            cwd=str(wt_path),
            capture_output=True,
        )

        # Merge into main
        success, msg = GitService.merge_branch(repo, "user/alice", into="main")
        assert success, msg
        assert (repo / "alice.md").exists()

    def test_merge_branch_conflict(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        # Create conflicting changes
        wt_path = tmp_path / "wt-conflict"
        GitService.worktree_add(repo, wt_path, "user/alice")

        # Change README on alice's branch
        (wt_path / "README.md").write_text("# Alice's version\n")
        subprocess.run(["git", "add", "."], cwd=str(wt_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Alice changes README"],
            cwd=str(wt_path),
            capture_output=True,
        )

        # Change README on main
        (repo / "README.md").write_text("# Main's version\n")
        subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Main changes README"],
            cwd=str(repo),
            capture_output=True,
        )

        # Merge should fail
        success, msg = GitService.merge_branch(repo, "user/alice", into="main")
        assert not success
        assert "conflict" in msg.lower() or "Merge" in msg

    def test_diff_branches(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        wt_path = tmp_path / "wt-diff"
        GitService.worktree_add(repo, wt_path, "user/alice")
        (wt_path / "new-entry.md").write_text("# New entry\n")
        subprocess.run(["git", "add", "."], cwd=str(wt_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add entry"],
            cwd=str(wt_path),
            capture_output=True,
        )

        success, diff = GitService.diff_branches(repo, "main", "user/alice")
        assert success
        assert "new-entry.md" in diff

        success, stat = GitService.diff_branches(repo, "main", "user/alice", stat_only=True)
        assert success
        assert "new-entry.md" in stat


class TestWorktreeService:
    """Test WorktreeService lifecycle against a real git repo + DB."""

    @pytest.fixture
    def setup(self, tmp_path):
        """Create a git repo, KB config, and PyriteDB."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_git_repo(repo)

        # Create a KB directory inside the repo
        kb_dir = repo / "kb"
        kb_dir.mkdir()
        (kb_dir / "test-entry.md").write_text(
            "---\nid: test-entry\ntitle: Test\ntype: note\n---\nBody\n"
        )
        subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add KB"],
            cwd=str(repo),
            capture_output=True,
        )

        config = _make_config(kb_dir, "test-kb")
        db = PyriteDB(tmp_path / "index.db")
        svc = WorktreeService(config, db)
        return {"repo": repo, "kb_dir": kb_dir, "config": config, "db": db, "svc": svc}

    def test_ensure_worktree_creates(self, setup):
        svc = setup["svc"]
        wt = svc.ensure_worktree("test-kb", user_id=1, username="alice")

        assert isinstance(wt, WorktreeInfo)
        assert wt.username == "alice"
        assert wt.kb_name == "test-kb"
        assert wt.branch == "user/alice"
        assert wt.status == "active"
        assert Path(wt.worktree_path).exists()

    def test_ensure_worktree_idempotent(self, setup):
        svc = setup["svc"]
        wt1 = svc.ensure_worktree("test-kb", user_id=1, username="alice")
        wt2 = svc.ensure_worktree("test-kb", user_id=1, username="alice")
        assert wt1.id == wt2.id
        assert wt1.worktree_path == wt2.worktree_path

    def test_get_worktree(self, setup):
        svc = setup["svc"]
        assert svc.get_worktree("test-kb", user_id=1) is None

        svc.ensure_worktree("test-kb", user_id=1, username="alice")
        wt = svc.get_worktree("test-kb", user_id=1)
        assert wt is not None
        assert wt.username == "alice"

    def test_list_worktrees(self, setup):
        svc = setup["svc"]
        svc.ensure_worktree("test-kb", user_id=1, username="alice")
        svc.ensure_worktree("test-kb", user_id=2, username="bob")

        wts = svc.list_worktrees("test-kb")
        assert len(wts) == 2
        names = {wt.username for wt in wts}
        assert names == {"alice", "bob"}

    def test_submit(self, setup):
        svc = setup["svc"]
        wt = svc.ensure_worktree("test-kb", user_id=1, username="alice")

        # Make a change in the worktree
        wt_path = Path(wt.worktree_path)
        (wt_path / "kb" / "new.md").write_text(
            "---\nid: new\ntitle: New\ntype: note\n---\nNew entry\n"
        )

        result = svc.submit("test-kb", user_id=1)
        assert result.status == "submitted"
        assert result.submitted_at is not None

    def test_get_submissions(self, setup):
        svc = setup["svc"]
        svc.ensure_worktree("test-kb", user_id=1, username="alice")
        svc.ensure_worktree("test-kb", user_id=2, username="bob")

        # Make changes and submit alice only
        wt = svc.get_worktree("test-kb", user_id=1)
        (Path(wt.worktree_path) / "kb" / "a.md").write_text(
            "---\nid: a\ntitle: A\ntype: note\n---\n"
        )
        svc.submit("test-kb", user_id=1)

        subs = svc.get_submissions("test-kb")
        assert len(subs) == 1
        assert subs[0].username == "alice"

    def test_reject(self, setup):
        svc = setup["svc"]
        svc.ensure_worktree("test-kb", user_id=1, username="alice")
        wt = svc.get_worktree("test-kb", user_id=1)
        (Path(wt.worktree_path) / "kb" / "a.md").write_text(
            "---\nid: a\ntitle: A\ntype: note\n---\n"
        )
        svc.submit("test-kb", user_id=1)

        result = svc.reject("test-kb", user_id=1, feedback="Needs more detail")
        assert result.status == "rejected"
        assert result.feedback == "Needs more detail"

    def test_merge(self, setup):
        svc = setup["svc"]
        repo = setup["repo"]

        wt = svc.ensure_worktree("test-kb", user_id=1, username="alice")
        wt_path = Path(wt.worktree_path)

        # Add a new file in the worktree
        (wt_path / "kb" / "alice-entry.md").write_text(
            "---\nid: alice-entry\ntitle: Alice Entry\ntype: note\n---\nAlice wrote this\n"
        )
        subprocess.run(["git", "add", "."], cwd=str(wt_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Alice's entry"],
            cwd=str(wt_path),
            capture_output=True,
        )

        success, msg = svc.merge("test-kb", user_id=1)
        assert success, msg
        # File should now exist in main repo
        assert (repo / "kb" / "alice-entry.md").exists()

        # Status should be merged
        wt = svc.get_worktree("test-kb", user_id=1)
        assert wt.status == "merged"

    def test_reset_to_main(self, setup):
        svc = setup["svc"]
        wt = svc.ensure_worktree("test-kb", user_id=1, username="alice")
        wt_path = Path(wt.worktree_path)

        # Make a change
        (wt_path / "kb" / "temp.md").write_text("temp\n")
        subprocess.run(["git", "add", "."], cwd=str(wt_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "temp"],
            cwd=str(wt_path),
            capture_output=True,
        )

        # Reset
        result = svc.reset_to_main("test-kb", user_id=1)
        assert result.status == "active"
        assert not (wt_path / "kb" / "temp.md").exists()

    def test_delete_worktree(self, setup):
        svc = setup["svc"]
        wt = svc.ensure_worktree("test-kb", user_id=1, username="alice")
        wt_path = Path(wt.worktree_path)
        assert wt_path.exists()

        result = svc.delete_worktree("test-kb", user_id=1)
        assert result is True
        assert not wt_path.exists()
        assert svc.get_worktree("test-kb", user_id=1) is None

    def test_get_user_kb_config(self, setup):
        svc = setup["svc"]
        svc.ensure_worktree("test-kb", user_id=1, username="alice")

        user_config = svc.get_user_kb_config("test-kb", user_id=1)
        assert user_config is not None
        assert user_config.name == "test-kb"
        assert "alice" in str(user_config.path)
        assert user_config.path != setup["config"].get_kb("test-kb").path

    def test_get_user_diff_db(self, setup):
        svc = setup["svc"]
        svc.ensure_worktree("test-kb", user_id=1, username="alice")

        diff_db = svc.get_user_diff_db("test-kb", user_id=1)
        assert diff_db is not None
        assert isinstance(diff_db, PyriteDB)
        diff_db.close()

    def test_no_worktree_returns_none(self, setup):
        svc = setup["svc"]
        assert svc.get_worktree("test-kb", user_id=99) is None
        assert svc.get_user_kb_config("test-kb", user_id=99) is None
        assert svc.get_user_diff_db("test-kb", user_id=99) is None
