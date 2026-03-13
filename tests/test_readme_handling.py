"""Tests for README.md handling in KB directories."""

from pathlib import Path

import pytest

from pyrite.config import PyriteConfig, Settings, KBConfig
from pyrite.storage.repository import KBRepository


@pytest.fixture
def kb_with_readme(tmp_path):
    """KB directory with a README.md and some entries."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()

    # Write a README without frontmatter
    (kb_path / "README.md").write_text("# My KB\n\nThis is a knowledge base.\n")

    # Write a valid entry
    (kb_path / "entry-1.md").write_text(
        "---\nid: entry-1\ntitle: Entry One\ntype: note\n---\nSome content.\n"
    )

    # Write a README in a subdirectory
    sub = kb_path / "notes"
    sub.mkdir()
    (sub / "README.md").write_text("# Notes\n\nNotes go here.\n")
    (sub / "note-1.md").write_text(
        "---\nid: note-1\ntitle: Note One\ntype: note\n---\nNote content.\n"
    )

    kb = KBConfig(name="test", path=kb_path, kb_type="standard")
    return KBRepository(kb)


class TestReadmeSkipping:
    """Test that README.md files are skipped during indexing."""

    def test_list_files_skips_readme(self, kb_with_readme):
        files = list(kb_with_readme.list_files())
        filenames = [f.name for f in files]
        assert "README.md" not in filenames
        assert "entry-1.md" in filenames
        assert "note-1.md" in filenames

    def test_list_files_skips_subdirectory_readme(self, kb_with_readme):
        files = list(kb_with_readme.list_files())
        # No README.md from notes/ either
        assert not any(f.name == "README.md" for f in files)

    def test_list_entries_no_errors_from_readme(self, kb_with_readme):
        """list_entries should not produce errors from README files."""
        entries = list(kb_with_readme.list_entries())
        # Should have 2 valid entries, no errors
        assert len(entries) == 2
        ids = {e[0].id for e in entries}
        assert "entry-1" in ids
        assert "note-1" in ids

    def test_count_excludes_readme(self, kb_with_readme):
        assert kb_with_readme.count() == 2

    def test_readme_case_insensitive(self, tmp_path):
        """readme.md (lowercase) should also be skipped."""
        kb_path = tmp_path / "test-kb"
        kb_path.mkdir()
        (kb_path / "readme.md").write_text("# readme\n")
        (kb_path / "entry-1.md").write_text(
            "---\nid: entry-1\ntitle: Entry\ntype: note\n---\nContent.\n"
        )
        kb = KBConfig(name="test", path=kb_path, kb_type="standard")
        repo = KBRepository(kb)
        files = list(repo.list_files())
        assert len(files) == 1
        assert files[0].name == "entry-1.md"
