"""Tests for scripts/check_fix_commit_has_tests.py -- ci-make-green-and-
load-bearing item 5: `fix:`-prefixed commits must touch tests/, mechanizing
Iron Law 1 (no production code without a failing test first) at the commit
boundary. Regression motivation: 40e7a39 shipped a fix with zero test
lines.

The `--range` tests below cover ci-parity-lint-extensions-and-enforce-the-
fix-needs-a-test-rule: the same rule, enforced in CI over a PR's whole
commit range (outside contributors' PRs never run the local commit-msg
hook), not just the single commit about to be made locally.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_fix_commit_has_tests.py"

sys.path.insert(0, str(SCRIPT.parent))

from check_fix_commit_has_tests import is_fix_commit, touches_tests  # noqa: E402


class TestIsFixCommit:
    def test_fix_prefix_is_a_fix_commit(self):
        assert is_fix_commit("fix: correct the thing\n\nBody here.") is True

    def test_feat_prefix_is_not_a_fix_commit(self):
        assert is_fix_commit("feat: add the thing") is False

    def test_docs_prefix_is_not_a_fix_commit(self):
        assert is_fix_commit("docs: fix the typo in README") is False

    def test_fix_must_be_at_start_of_subject(self):
        """'fix' appearing later in the subject doesn't count -- only a
        literal 'fix:' prefix on the subject line."""
        assert is_fix_commit("refactor: fix up naming (not a fix: commit)") is False

    def test_empty_message_is_not_a_fix_commit(self):
        assert is_fix_commit("") is False


class TestTouchesTests:
    def test_top_level_tests_dir_counts(self):
        assert touches_tests(["tests/test_foo.py", "pyrite/foo.py"]) is True

    def test_extension_tests_dir_counts(self):
        assert touches_tests(["extensions/software-kb/tests/test_bar.py"]) is True

    def test_no_test_files_is_false(self):
        assert touches_tests(["pyrite/foo.py", "README.md"]) is False

    def test_empty_list_is_false(self):
        assert touches_tests([]) is False

    def test_path_containing_tests_substring_but_not_dir_does_not_count(self):
        """A filename like 'latest_stats.py' contains the substring 'test'
        but is not under a tests/ directory -- must not false-positive."""
        assert touches_tests(["pyrite/latest_stats.py"]) is False


class TestRangeMode:
    """`--range BASE HEAD` walks each commit in BASE..HEAD, the mode CI uses
    (a PR's commits, not the one about to be made locally)."""

    def _git(self, repo, *args):
        return subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
            env={
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@example.com",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@example.com",
                "PATH": "/usr/bin:/bin:/usr/local/bin",
            },
        )

    def _commit(self, repo, path: str, message: str, content: str = "x"):
        f = repo / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
        self._git(repo, "add", path)
        self._git(repo, "commit", "-m", message)

    def _repo(self, tmp_path):
        repo = tmp_path / "scratch"
        repo.mkdir()
        self._git(repo, "init", "-q")
        self._commit(repo, "README.md", "chore: seed", "seed")
        return repo

    def test_range_passes_when_fix_commit_touches_tests(self, tmp_path):
        repo = self._repo(tmp_path)
        base = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        self._commit(repo, "tests/test_thing.py", "fix: correct the thing")
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--range", base, head],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_range_fails_when_fix_commit_touches_no_tests(self, tmp_path):
        repo = self._repo(tmp_path)
        base = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        self._commit(repo, "pyrite/thing.py", "fix: correct the thing without a test")
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--range", base, head],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "fix:" in result.stderr
        assert "tests/" in result.stderr

    def test_range_ignores_non_fix_commits_without_tests(self, tmp_path):
        repo = self._repo(tmp_path)
        base = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        self._commit(repo, "pyrite/thing.py", "feat: add the thing")
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--range", base, head],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_range_checks_every_commit_not_just_the_last(self, tmp_path):
        repo = self._repo(tmp_path)
        base = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        self._commit(repo, "pyrite/a.py", "fix: first fix, no test")
        self._commit(repo, "tests/test_b.py", "feat: unrelated, has a test dir file anyway")
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--range", base, head],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        # The offending commit is the FIRST one; a naive "does the whole
        # range touch tests/" check would wrongly pass because the second
        # commit happens to add a tests/ file.
        assert result.returncode != 0, result.stderr
