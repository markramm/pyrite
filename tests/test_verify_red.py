"""scripts/verify-red.sh must revert a COMMITTED fix, or refuse to make a claim.

#121: the previous version used `git stash push -- <files>`, which on a branch
whose fix is already committed saves nothing, exits 0, and runs the test
against the fix -- so every "fails without the fix" claim on PR #69 was
unverified. These tests build a real repository with a base commit, a fix
commit and a test, and check each exit code the script promises.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-red.sh"

IMPL_BROKEN = "def add(a, b):\n    return a - b\n"
IMPL_FIXED = "def add(a, b):\n    return a + b\n"
TEST_REAL = "from impl import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n"
TEST_VACUOUS = "from impl import add\n\n\ndef test_add():\n    assert callable(add)\n"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo whose `dev` has the broken impl and a branch that commits the fix."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "dev")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    (r / ".gitignore").write_text("__pycache__/\n")
    (r / "impl.py").write_text(IMPL_BROKEN)
    (r / "other.py").write_text("x = 1\n")  # present and unchanged on both sides
    (r / "test_impl.py").write_text(TEST_REAL)
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "base: broken impl and its test")
    git(r, "checkout", "-q", "-b", "fix/add")
    (r / "impl.py").write_text(IMPL_FIXED)
    git(r, "commit", "-q", "-am", "fix: add adds")
    return r


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "VERIFY_RED_BASE": "dev", "VERIFY_RED_PYTHON": sys.executable}
    return subprocess.run(
        ["bash", str(SCRIPT), *args], cwd=repo, env=env, capture_output=True, text=True
    )


def test_a_committed_fix_is_reverted_and_the_real_test_goes_red(repo: Path) -> None:
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 0, result.stderr
    assert "fails without the fix" in result.stdout
    # The tree is restored afterwards.
    assert (repo / "impl.py").read_text() == IMPL_FIXED
    assert git(repo, "status", "--porcelain") == ""


def test_a_test_that_passes_without_the_fix_is_reported(repo: Path) -> None:
    (repo / "test_impl.py").write_text(TEST_VACUOUS)
    git(repo, "commit", "-q", "-am", "test: vacuous")
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 1
    assert "PASSED without the fix" in result.stderr
    assert (repo / "impl.py").read_text() == IMPL_FIXED


def test_files_unchanged_since_the_merge_base_are_refused_not_verified(repo: Path) -> None:
    # #121's exact failure: naming a file the fix did not touch must not yield a verdict.
    result = run(repo, "test_impl.py::test_add", "other.py")
    assert result.returncode == 2
    assert "nothing was reverted" in result.stderr


def test_uncommitted_changes_to_the_impl_are_refused(repo: Path) -> None:
    (repo / "impl.py").write_text(IMPL_FIXED + "# wip\n")
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 2
    assert "uncommitted changes" in result.stderr
    assert (repo / "impl.py").read_text() == IMPL_FIXED + "# wip\n"


def test_a_file_new_on_the_branch_is_removed_for_the_run_and_restored(repo: Path) -> None:
    (repo / "helper.py").write_text("def helper():\n    return 4\n")
    (repo / "impl.py").write_text(
        "from helper import helper\n\n\ndef add(a, b):\n    return helper()\n"
    )
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: via a new helper module")
    result = run(repo, "test_impl.py::test_add", "impl.py", "helper.py")
    assert result.returncode == 0, result.stderr
    assert (repo / "helper.py").exists()
    assert git(repo, "status", "--porcelain") == ""
