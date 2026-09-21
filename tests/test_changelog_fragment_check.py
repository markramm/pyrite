"""The advisory check that notices a PR recording no changelog fragment (#278).

#173 merged with no fragment: its entry went into `CHANGELOG.md` under the
already-released `## [0.24.3]` heading, so `tests/test_changelog_fragments.py`
-- which asserts `[Unreleased]` stays empty -- had nothing to complain about,
and the fix was absent from the assembled release notes. That is the case this
check exists to catch.

It warns rather than fails, so these tests assert on the *decision*
(`verdict()`), not on an exit status. `verdict()` is deliberately I/O-free for
exactly that reason.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _load():
    path = REPO / "scripts" / "check_changelog_fragment.py"
    spec = importlib.util.spec_from_file_location("check_changelog_fragment", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def check():
    return _load()


class TestWarns:
    def test_shipped_code_with_no_fragment(self, check):
        files = ["pyrite/storage/backends/postgres_backend.py", "tests/test_x.py"]
        message = check.verdict(files, body="")
        assert message is not None
        assert "postgres_backend.py" in message
        assert "changelog.d/" in message

    def test_the_173_shape(self, check):
        """#173's actual diff: shipped code, tests, and CHANGELOG.md -- but the
        entry went under a released heading, so no fragment was added."""
        files = ["pyrite/models/generic.py", "tests/test_models.py", "CHANGELOG.md"]
        assert check.verdict(files, body="") is not None

    def test_extensions_count_as_shipped(self, check):
        files = ["extensions/zettelkasten/pyrite_zettelkasten/tools.py"]
        assert check.verdict(files, body="") is not None


class TestStaysQuiet:
    def test_a_fragment_is_present(self, check):
        files = ["pyrite/cli.py", "changelog.d/my-change.fixed.md"]
        assert check.verdict(files, body="") is None

    def test_test_only_change(self, check):
        files = ["tests/test_one.py", "tests/backends/conftest.py"]
        assert check.verdict(files, body="") is None

    def test_ci_only_change(self, check):
        files = [".github/workflows/ci.yml", "scripts/check_changelog_fragment.py"]
        assert check.verdict(files, body="") is None

    def test_docs_and_kb_only(self, check):
        files = ["README.md", "kb/roadmap.md", "docs/getting-started.md"]
        assert check.verdict(files, body="") is None

    def test_explicit_opt_out(self, check):
        files = ["pyrite/services/kb_service.py"]
        body = "Pure refactor, no behaviour change.\n\nChangelog: none\n"
        assert check.verdict(files, body=body) is None

    @pytest.mark.parametrize(
        "body",
        ["Changelog: none", "changelog: none", "  Changelog:  none  (refactor)"],
    )
    def test_opt_out_spellings(self, check, body):
        assert check.verdict(["pyrite/cli.py"], body=body) is None

    def test_empty_diff(self, check):
        assert check.verdict([], body="") is None


class TestDoesNotMisfire:
    def test_changelog_md_alone_is_not_a_fragment(self, check):
        """Editing CHANGELOG.md is not recording a fragment -- that is #173."""
        files = ["pyrite/cli.py", "CHANGELOG.md"]
        assert check.verdict(files, body="") is not None

    def test_a_passing_mention_does_not_opt_out(self, check):
        """'changelog' in prose must not silence the check."""
        body = "This updates the changelog handling. No opt-out intended."
        assert check.verdict(["pyrite/cli.py"], body=body) is not None

    def test_readme_in_changelog_dir_is_not_a_fragment(self, check):
        # changelog.d/README.md is documentation, not an entry. It ends in .md
        # and lives in changelog.d/, so a naive check would treat it as one.
        files = ["pyrite/cli.py", "changelog.d/README.md"]
        assert check.verdict(files, body="") is not None

    def test_non_entries_agree_with_the_release_script(self, check):
        """The two lists must not drift apart.

        If this check counted a file the release script skips, a PR would be
        told it had recorded a change that the notes would never report --
        exactly the #173 failure, arrived at from the other direction.
        """
        spec = importlib.util.spec_from_file_location(
            "release_for_test", REPO / "scripts" / "release.py"
        )
        release = importlib.util.module_from_spec(spec)
        # release.py defines @dataclass types, and dataclasses resolves a
        # class's module through sys.modules -- so it has to be registered
        # before exec_module, not after.
        sys.modules["release_for_test"] = release
        try:
            spec.loader.exec_module(release)
            assert check.FRAGMENT_NON_ENTRIES == release.FRAGMENT_NON_ENTRIES
        finally:
            sys.modules.pop("release_for_test", None)
