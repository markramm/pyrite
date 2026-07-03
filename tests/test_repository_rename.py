"""Tests for KBRepository.rename — Tier A r1700 rename-move-support.

Pyrite has no first-class command for renaming an entry. In practice
that means internal wikilinks break silently when an entry is renamed,
and users avoid renaming even when the new name is clearly better,
because the cleanup cost is high enough that the KB accumulates
slug-drift. This test pins the contract for the smallest useful slice:

  - rename file on disk
  - rewrite frontmatter `id:` field
  - rewrite `[[<old-id>]]` and `[[<old-id>|alias]]` wikilinks within
    the same KB
  - dry-run mode that shows the plan without executing
  - error on target collision and missing source

Cross-KB wikilink rewrite, redirect-stub creation, and the `move`
variant (subdir change) are filed as r1700 follow-ups.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, KBType
from pyrite.exceptions import EntryNotFoundError, ValidationError
from pyrite.models import NoteEntry
from pyrite.storage.repository import KBRepository


@pytest.fixture
def repo_with_links():
    """Repo with 3 entries; entry-b and entry-c link to entry-a."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir) / "kb"
        kb_path.mkdir()
        kb = KBConfig(name="test-kb", path=kb_path, kb_type=KBType.GENERIC)
        repo = KBRepository(kb)

        repo.save(NoteEntry(id="entry-a", title="A", body="I am A."))
        repo.save(
            NoteEntry(
                id="entry-b",
                title="B",
                body="See [[entry-a]] for context.",
            )
        )
        repo.save(
            NoteEntry(
                id="entry-c",
                title="C",
                body=(
                    "Mentions [[entry-a|the original A]] and a separate "
                    "[[entry-a]] link, plus an unrelated [[entry-b]]."
                ),
            )
        )
        yield repo


class TestRename:
    """Core rename: file move + frontmatter id rewrite + wikilink rewrite."""

    def test_rename_moves_file_to_new_id(self, repo_with_links):
        result = repo_with_links.rename("entry-a", "renamed-a")
        # File moved on disk
        assert (repo_with_links.path / "notes" / "renamed-a.md").exists()
        assert not (repo_with_links.path / "notes" / "entry-a.md").exists()
        # Result reports the rename
        assert result["renamed"] is True
        assert result["old_id"] == "entry-a"
        assert result["new_id"] == "renamed-a"

    def test_rename_rewrites_frontmatter_id(self, repo_with_links):
        repo_with_links.rename("entry-a", "renamed-a")
        loaded = repo_with_links.load("renamed-a")
        assert loaded is not None
        assert loaded.id == "renamed-a"

    def test_rename_rewrites_bare_wikilinks(self, repo_with_links):
        """[[entry-a]] in entry-b's body becomes [[renamed-a]]."""
        repo_with_links.rename("entry-a", "renamed-a")
        b = repo_with_links.load("entry-b")
        assert b is not None
        assert "[[renamed-a]]" in b.body
        assert "[[entry-a]]" not in b.body

    def test_rename_rewrites_aliased_wikilinks(self, repo_with_links):
        """[[entry-a|the original A]] becomes [[renamed-a|the original A]] —
        alias text is preserved."""
        repo_with_links.rename("entry-a", "renamed-a")
        c = repo_with_links.load("entry-c")
        assert c is not None
        assert "[[renamed-a|the original A]]" in c.body
        # Bare link in same body also rewrote
        assert "[[renamed-a]]" in c.body
        # Unrelated link untouched
        assert "[[entry-b]]" in c.body
        # No leftover old-id links
        assert "[[entry-a]]" not in c.body
        assert "[[entry-a|" not in c.body

    def test_rename_returns_link_rewrite_count(self, repo_with_links):
        """Result dict reports how many files had wikilinks rewritten so
        the CLI can surface it."""
        result = repo_with_links.rename("entry-a", "renamed-a")
        # entry-b (1 rewrite) + entry-c (2 rewrites in one file)
        assert result["files_rewritten"] == 2
        assert result["links_rewritten"] >= 3


class TestRenameDryRun:
    """Dry-run mode: surface the plan, change nothing."""

    def test_dry_run_does_not_modify_filesystem(self, repo_with_links):
        result = repo_with_links.rename("entry-a", "renamed-a", dry_run=True)
        # Nothing changed on disk
        assert (repo_with_links.path / "notes" / "entry-a.md").exists()
        assert not (repo_with_links.path / "notes" / "renamed-a.md").exists()
        # entry-b body still references the OLD id
        b = repo_with_links.load("entry-b")
        assert "[[entry-a]]" in b.body
        # Result still reports what WOULD happen
        assert result["dry_run"] is True
        assert result["old_id"] == "entry-a"
        assert result["new_id"] == "renamed-a"
        assert result["files_rewritten"] == 2  # planned, not actual


class TestRenameNoUpdateLinks:
    """update_links=False: rename the file but leave wikilinks alone.

    Rare case — sometimes the user intentionally wants old references
    preserved (e.g., for historical study). The default is True.
    """

    def test_no_update_links_leaves_wikilinks_unchanged(self, repo_with_links):
        result = repo_with_links.rename("entry-a", "renamed-a", update_links=False)
        assert (repo_with_links.path / "notes" / "renamed-a.md").exists()
        b = repo_with_links.load("entry-b")
        # Old link still there — now dangling
        assert "[[entry-a]]" in b.body
        assert result["files_rewritten"] == 0
        assert result["links_rewritten"] == 0


class TestRenameErrors:
    """Error paths: missing source, target collision."""

    def test_rename_missing_source_raises(self, repo_with_links):
        with pytest.raises(EntryNotFoundError):
            repo_with_links.rename("no-such-entry", "anything")

    def test_rename_target_exists_raises(self, repo_with_links):
        """Refuse to clobber an existing entry."""
        with pytest.raises(ValidationError):
            repo_with_links.rename("entry-a", "entry-b")

    def test_rename_same_id_is_noop(self, repo_with_links):
        """rename(x, x) is a no-op, not an error — callers may script it."""
        result = repo_with_links.rename("entry-a", "entry-a")
        assert result["renamed"] is False
        assert (repo_with_links.path / "notes" / "entry-a.md").exists()
