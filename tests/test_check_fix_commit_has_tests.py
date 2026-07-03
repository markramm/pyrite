"""Tests for scripts/check_fix_commit_has_tests.py -- ci-make-green-and-
load-bearing item 5: `fix:`-prefixed commits must touch tests/, mechanizing
Iron Law 1 (no production code without a failing test first) at the commit
boundary. Regression motivation: 40e7a39 shipped a fix with zero test
lines.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

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
