"""End-to-end test for the editor review flow (Amy editing drafts).

Exercises the real code path the API uses:
  1. A non-admin user's edit routes through WorktreeResolver.get_write_service
     into their personal git worktree (body edit + metadata.review_comments).
  2. The user submits; an admin merges.
  3. The merged draft on main contains BOTH the prose edit and the comments,
     proving comments ride the worktree->merge flow into the KB for automation.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from pyrite.services.worktree_service import WorktreeService
from pyrite.server.worktree_resolver import WorktreeResolver
from pyrite.storage.database import PyriteDB


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, check=True)


def _init_repo(path: Path) -> None:
    _git(["init"], path)
    _git(["config", "user.email", "t@t.com"], path)
    _git(["config", "user.name", "T"], path)
    (path / "README.md").write_text("# KB\n")
    _git(["add", "."], path)
    _git(["commit", "-m", "init"], path)


def _make_config(kb_path: Path, kb_name="drafts"):
    from pyrite.config import KBConfig, PyriteConfig, Settings

    kb = KBConfig(name=kb_name, path=kb_path, kb_type="generic")
    return PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=Path(tempfile.mkdtemp()) / "index.db"),
    )


@pytest.fixture
def env(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    kb_dir = repo / "kb"
    kb_dir.mkdir()
    (kb_dir / "my-draft.md").write_text(
        "---\nid: my-draft\ntitle: My Draft\ntype: note\n---\nOriginal body text.\n"
    )
    _git(["add", "."], repo)
    _git(["commit", "-m", "add draft"], repo)

    config = _make_config(kb_dir, "drafts")
    db = PyriteDB(tmp_path / "index.db")
    # Register + index the main KB, as the server does at startup. This creates
    # the parent `kb` row the worktree overlay's entry writes reference.
    from pyrite.storage.index import IndexManager

    IndexManager(db, config).index_kb("drafts")
    wt_svc = WorktreeService(config, db)
    # WorktreeResolver builds its own WorktreeService internally; the third arg
    # is a per-request diff-db cache.
    resolver = WorktreeResolver(config, db, {})
    return {
        "repo": repo,
        "kb_dir": kb_dir,
        "config": config,
        "db": db,
        "wt_svc": wt_svc,
        "resolver": resolver,
    }


def test_amy_edit_and_comment_merges_into_kb(env):
    resolver = env["resolver"]
    wt_svc = env["wt_svc"]
    repo = env["repo"]

    amy = {"id": 1, "username": "amy", "role": "write"}

    # 1. Amy edits the body AND adds a review comment, via the API's write path.
    write_svc = resolver.get_write_service("drafts", amy)
    write_svc.update_entry(
        "my-draft",
        "drafts",
        body="Original body text. Amy's copyedit.",
        metadata={
            "review_comments": [
                {
                    "id": "c-1",
                    "author": "amy",
                    "created_at": "2026-05-29T14:00:00Z",
                    "quote": "Amy's copyedit",
                    "context_before": "Original body text. ",
                    "context_after": ".",
                    "note": "not sure about this phrasing",
                    "status": "open",
                }
            ]
        },
    )

    # The worktree file should reflect both changes before merge. (The entry may
    # be filed under a type subdirectory, so locate it by name.)
    wt = wt_svc.get_worktree("drafts", user_id=1)
    wt_files = list((Path(wt.worktree_path) / "kb").rglob("my-draft.md"))
    assert wt_files, "draft not found in worktree"
    wt_text = wt_files[0].read_text()
    assert "Amy's copyedit" in wt_text
    assert "review_comments" in wt_text
    assert "not sure about this phrasing" in wt_text

    # Commit Amy's work in her worktree, then submit.
    _git(["add", "."], wt.worktree_path)
    _git(["commit", "-m", "amy edits"], wt.worktree_path)
    wt_svc.submit("drafts", user_id=1)

    # 2. Admin reviews the diff and merges.
    from pyrite.services.git_service import GitService

    ok, diff = GitService.diff_branches(repo, "main", "user/amy")
    assert ok
    assert "Amy's copyedit" in diff
    assert "review_comments" in diff
    # The worktree's own diff index must not leak into the branch/diff.
    assert "diff-index.db" not in diff

    ok, msg = wt_svc.merge("drafts", user_id=1)
    assert ok, msg

    # 3. The merged draft on main carries both the edit and the comments —
    #    i.e. the automation pipeline reading the KB will see them.
    merged_files = list((repo / "kb").rglob("my-draft.md"))
    assert merged_files, "draft not found on main after merge"
    merged = merged_files[0].read_text()
    assert "Amy's copyedit" in merged
    assert "review_comments" in merged
    assert "not sure about this phrasing" in merged
