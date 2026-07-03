"""Regression test: `pyrite schema validate --changed` must only validate
files that live inside a configured KB, not every changed .md file in the
repo.

Found while fixing ci-make-green-and-load-bearing's pyrite-schema-validate
pre-commit hook: once the hook's `python -m pyrite` invocation bug was
fixed and it could actually run, it immediately flagged non-KB markdown
(e.g. .claude/skills/*.md) as invalid KB entries for lacking frontmatter.
_get_git_changed_md_files() collected every changed .md path repo-wide
with no KB-path filtering.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from pyrite.cli.schema_commands import _get_git_changed_md_files
from pyrite.config import KBConfig, PyriteConfig, Settings


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, check=True)


@pytest.fixture
def repo_with_kb_and_non_kb_changes(monkeypatch):
    """A git repo with a KB directory and a non-KB directory, each with an
    uncommitted (untracked) .md file -- the "changed files" scenario the
    pre-commit hook actually hits."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(["init"], repo)
        _git(["config", "user.email", "t@t.com"], repo)
        _git(["config", "user.name", "T"], repo)
        (repo / "README.md").write_text("# repo\n")
        _git(["add", "."], repo)
        _git(["commit", "-m", "init"], repo)

        kb_path = repo / "kb"
        kb_path.mkdir()
        (kb_path / "entry.md").write_text("---\ntype: note\ntitle: Entry\n---\nBody\n")

        non_kb_path = repo / "docs"
        non_kb_path.mkdir()
        (non_kb_path / "guide.md").write_text("# Just a doc, no frontmatter\n")

        monkeypatch.chdir(repo)

        config = PyriteConfig(
            knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
            settings=Settings(index_path=repo / "index.db"),
        )
        yield {"repo": repo, "kb_path": kb_path, "non_kb_path": non_kb_path, "config": config}


class TestGitChangedMdFilesKBScoping:
    def test_filters_to_kb_paths_only(self, repo_with_kb_and_non_kb_changes):
        env = repo_with_kb_and_non_kb_changes
        result = _get_git_changed_md_files(env["config"].all_kbs())

        result_names = {p.name for p in result}
        assert "entry.md" in result_names, "the KB-scoped file must still be included"
        assert "guide.md" not in result_names, (
            f"a changed .md file outside every configured KB must be excluded -- got {result_names}"
        )

    def test_no_kb_filter_arg_preserves_old_behavior(self, repo_with_kb_and_non_kb_changes):
        """Backward compatibility: calling with no filter (or an empty list)
        returns every changed .md file, same as before this fix."""
        env = repo_with_kb_and_non_kb_changes
        result = _get_git_changed_md_files([])

        result_names = {p.name for p in result}
        assert "entry.md" in result_names
        assert "guide.md" in result_names
