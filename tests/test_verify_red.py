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


# ---------------------------------------------------------------------------
# #189: a review worktree whose .venv is a symlink to the main checkout's
# resolves `pyrite` (and every extension package) to an EDITABLE INSTALL
# pointing at the main checkout on `dev`, not the branch under review, even
# though the interpreter itself lives "in" the worktree. verify-red.sh must
# refuse to report a suite number in that situation: it has to resolve the
# top-level package for each reverted production file and confirm the
# INTERPRETER'S import of that package resolves under the worktree.
# ---------------------------------------------------------------------------


@pytest.fixture
def pkg_repo(tmp_path: Path) -> Path:
    """Like `repo`, but the reverted file is `pyrite/__init__.py` (a package)."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "dev")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    (r / ".gitignore").write_text("__pycache__/\n")
    pkg = r / "pyrite"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("def add(a, b):\n    return a - b\n")
    (r / "test_impl.py").write_text(
        "from pyrite import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n"
    )
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "base: broken impl and its test")
    git(r, "checkout", "-q", "-b", "fix/add")
    (pkg / "__init__.py").write_text("def add(a, b):\n    return a + b\n")
    git(r, "commit", "-q", "-am", "fix: add adds")
    return r


def _make_wrapper_python(tmp_path: Path, extra_sys_path: Path) -> Path:
    """A fake `python` that resolves `import pyrite` to `extra_sys_path`, not cwd.

    Simulates a symlinked venv: the interpreter binary is real, but an
    editable install (a .pth-style entry in site-packages) makes `import
    pyrite` resolve to another checkout entirely. PYTHONPATH puts the
    external package on sys.path; PYTHONSAFEPATH (3.11+) drops the implicit
    cwd entry that would otherwise let a same-named local directory shadow
    it -- matching the real bug, where the worktree has no local install of
    its own `pyrite` at all, only the editable install pointing elsewhere.
    """
    wrapper = tmp_path / "fake-python"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        f'export PYTHONPATH="{extra_sys_path}${{PYTHONPATH:+:$PYTHONPATH}}"\n'
        "export PYTHONSAFEPATH=1\n"
        f'exec {sys.executable} "$@"\n'
    )
    wrapper.chmod(0o755)
    return wrapper


def test_package_resolving_outside_the_worktree_is_refused(pkg_repo: Path, tmp_path: Path) -> None:
    # An external "other checkout" with its OWN pyrite package -- this is what
    # a symlinked .venv's editable install points at instead of the worktree.
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "pyrite").mkdir(parents=True)
    (elsewhere / "pyrite" / "__init__.py").write_text("def add(a, b):\n    return a + b\n")

    wrapper = _make_wrapper_python(tmp_path, elsewhere)

    env = {
        **os.environ,
        "VERIFY_RED_BASE": "dev",
        "VERIFY_RED_PYTHON": str(wrapper),
    }
    result = subprocess.run(
        ["bash", str(SCRIPT), "test_impl.py::test_add", "pyrite/__init__.py"],
        cwd=pkg_repo,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "not importing" in result.stderr or "resolves outside" in result.stderr, result.stderr
    # The tree is still restored even though the claim was refused.
    assert (pkg_repo / "pyrite" / "__init__.py").read_text() == "def add(a, b):\n    return a + b\n"


def test_package_resolving_inside_the_worktree_still_runs(pkg_repo: Path) -> None:
    # The normal case: the venv's own interpreter, pyrite resolves under the
    # worktree itself. Must behave exactly as before -- red without the fix.
    result = run(pkg_repo, "test_impl.py::test_add", "pyrite/__init__.py")
    assert result.returncode == 0, result.stderr
    assert "fails without the fix" in result.stdout
    assert (pkg_repo / "pyrite" / "__init__.py").read_text() == "def add(a, b):\n    return a + b\n"


# ---------------------------------------------------------------------------
# One owner for the revert and the restore (retro 10, #368): verify-red.sh is
# a wrapper over scripts/verify_red_ci.py, which writes the files itself and
# never through `git checkout`, so the index is never touched.
# ---------------------------------------------------------------------------


def _index(repo: Path) -> bytes:
    return (repo / ".git" / "index").read_bytes()


def test_the_index_is_never_written(repo: Path) -> None:
    before = _index(repo)
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 0, result.stderr
    assert _index(repo) == before
    assert (repo / "impl.py").read_text() == IMPL_FIXED


def test_a_crlf_checkout_verifies_and_comes_back_byte_for_byte(repo: Path) -> None:
    (repo / ".gitattributes").write_text("*.py text eol=crlf\n")
    git(repo, "add", ".gitattributes")
    git(repo, "commit", "-q", "-m", "crlf")
    crlf = IMPL_FIXED.replace("\n", "\r\n").encode()
    (repo / "impl.py").unlink()
    git(repo, "checkout", "--", "impl.py")  # as a checkout under the attribute writes it
    assert (repo / "impl.py").read_bytes() == crlf
    assert git(repo, "status", "--porcelain") == ""
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 0, result.stderr
    assert (repo / "impl.py").read_bytes() == crlf


def test_a_test_id_that_names_no_test_is_no_claim(repo: Path) -> None:
    # pytest exits 4 (no such node) or 5 (nothing collected): a failure to run is
    # not "fails without the fix".
    result = run(repo, "test_impl.py::test_does_not_exist", "impl.py")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "no claim" in result.stderr
    assert (repo / "impl.py").read_text() == IMPL_FIXED


def test_an_uncommitted_deletion_is_refused(repo: Path) -> None:
    (repo / "impl.py").unlink()
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 2
    assert "uncommitted changes" in result.stderr
    assert not (repo / "impl.py").exists()


def test_stale_bytecode_is_not_served_to_the_reverted_run(repo: Path) -> None:
    # A .pyc that Python does not check against its source (or a timestamp one
    # whose same-second, same-size source was swapped under it) would run the fix
    # in the "without the fix" run. The revert drops the file's bytecode.
    import importlib.util
    import py_compile

    src = repo / "impl.py"
    py_compile.compile(
        str(src),
        cfile=importlib.util.cache_from_source(str(src)),
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_interrupting_the_wrapper_restores_the_tree(repo: Path, tmp_path: Path) -> None:
    import signal
    import time

    pidfile = tmp_path / "hung.pid"
    (repo / "impl.py").write_text(
        "import os\nimport time\n\n\ndef add(a, b):\n"
        f"    open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
        "    time.sleep(120)\n    return a - b\n"
    )
    git(repo, "commit", "-q", "--amend", "-am", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    (repo / "impl.py").write_text(IMPL_FIXED)
    git(repo, "commit", "-q", "-am", "fix: add adds, promptly")
    before = _index(repo)

    env = {**os.environ, "VERIFY_RED_BASE": "dev", "VERIFY_RED_PYTHON": sys.executable}
    proc = subprocess.Popen(
        ["bash", str(SCRIPT), "test_impl.py::test_add", "impl.py"],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 60
        while not (pidfile.exists() and pidfile.read_text().strip()):
            assert proc.poll() is None, "the wrapper exited before the run hung"
            assert time.monotonic() < deadline, "the reverted run never started"
            time.sleep(0.1)
        hung = int(pidfile.read_text())
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode != 0
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(hung, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        os.kill(hung, signal.SIGKILL)
        pytest.fail("the pytest run outlived the wrapper")
    assert (repo / "impl.py").read_text() == IMPL_FIXED
    assert _index(repo) == before


def test_an_interpreter_that_cannot_import_the_package_is_refused(tmp_path: Path) -> None:
    # An extension package no interpreter on this machine installs: the import
    # fails, so which tree the run would test is unknown -- no claim.
    r = tmp_path / "repo"
    src = r / "extensions" / "ext" / "src" / "verify_red_nopkg"
    src.mkdir(parents=True)
    git(r, "init", "-q", "-b", "dev")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    (src / "__init__.py").write_text(IMPL_BROKEN)
    (r / "test_impl.py").write_text(TEST_REAL.replace("from impl", "from verify_red_nopkg"))
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "base")
    git(r, "checkout", "-q", "-b", "fix/add")
    (src / "__init__.py").write_text(IMPL_FIXED)
    git(r, "commit", "-q", "-am", "fix")
    result = run(r, "test_impl.py::test_add", "extensions/ext/src/verify_red_nopkg/__init__.py")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "cannot confirm which tree" in result.stderr
    assert (src / "__init__.py").read_text() == IMPL_FIXED


def test_the_base_falls_back_to_dev_without_origin(repo: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "VERIFY_RED_BASE"}
    env["VERIFY_RED_PYTHON"] = sys.executable
    result = subprocess.run(
        ["bash", str(SCRIPT), "test_impl.py::test_add", "impl.py"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (repo / "impl.py").read_text() == IMPL_FIXED


def test_the_driver_needs_files_to_revert(repo: Path) -> None:
    driver = SCRIPT.with_name("verify_red_ci.py")
    result = subprocess.run(
        [sys.executable, str(driver), "--base", "dev", "--test", "test_impl.py::test_add"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "name the implementation files" in result.stderr


def test_the_file_mode_survives_the_revert_and_the_restore(repo: Path) -> None:
    (repo / "impl.py").chmod(0o755)
    git(repo, "commit", "-q", "-am", "impl is executable")
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 0, result.stderr
    assert (repo / "impl.py").stat().st_mode & 0o777 == 0o755
    assert git(repo, "status", "--porcelain") == ""


# ---------------------------------------------------------------------------
# The verdict matches CI mode: pytest's exit 1 is red; a collection error is a
# (weak) red, whatever exit it produced -- 2 for a file, 4 for a node id that
# the failed import hid; anything else (a killed run, an internal error, an
# interrupted session) is no claim.
# ---------------------------------------------------------------------------


def _commit_test(repo: Path, text: str) -> None:
    (repo / "test_impl.py").write_text(text)
    git(repo, "commit", "-q", "-am", "test")


def _commit_impl_pair(repo: Path, broken: str, fixed: str) -> None:
    git(repo, "checkout", "-q", "dev")
    (repo / "impl.py").write_text(broken)
    git(repo, "commit", "-q", "--allow-empty", "-am", "base impl")
    git(repo, "checkout", "-q", "-B", "fix/add")
    (repo / "impl.py").write_text(fixed)
    git(repo, "commit", "-q", "-am", "fix impl")


def test_a_collection_error_is_a_weak_red(repo: Path) -> None:
    _commit_impl_pair(repo, IMPL_BROKEN, IMPL_FIXED + "\n\ndef helper():\n    return 1\n")
    _commit_test(repo, "from impl import helper\n\n\ndef test_add():\n    assert helper() == 1\n")
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "collection error" in result.stdout


@pytest.mark.parametrize(
    "broken",
    [
        # the run is killed (the OOM killer): pytest's exit is -9
        "import os\nimport signal\n\n\ndef add(a, b):\n    os.kill(os.getpid(), signal.SIGKILL)\n",
        # the session is interrupted inside a test: exit 2, no collection error
        "def add(a, b):\n    raise KeyboardInterrupt\n",
    ],
    ids=["killed", "interrupted"],
)
def test_a_run_that_did_not_finish_is_no_claim(repo: Path, broken: str) -> None:
    _commit_impl_pair(repo, broken, IMPL_FIXED)
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "no claim" in result.stderr
    assert (repo / "impl.py").read_text() == IMPL_FIXED


def test_a_pytest_internal_error_is_no_claim(repo: Path) -> None:
    # exit 3: a plugin hook raised -- only in the reverted run.
    (repo / "conftest.py").write_text(
        "import impl\n\n\ndef pytest_runtest_logreport(report):\n"
        "    if impl.add(2, 2) != 4:\n        raise RuntimeError('boom')\n"
    )
    git(repo, "add", "conftest.py")
    git(repo, "commit", "-q", "-m", "conftest")
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "no claim" in result.stderr


def test_contributing_names_what_the_restore_covers_and_what_it_cannot() -> None:
    # "however the run ends" over-promised: SIGKILL cannot be caught.
    text = " ".join((SCRIPT.parents[1] / "CONTRIBUTING.md").read_text().split())
    para = text[text.index("Reviews run `scripts/verify-red.sh") :][:1200]
    assert "however the run ends" not in para
    for covered in ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT", "SIGKILL"):
        assert covered in para, covered


def test_a_symlinked_impl_file_is_refused_not_replaced(repo: Path) -> None:
    # Same bytes as HEAD through the link, but the revert would write a regular
    # file in its place and the restore would never make the link again.
    (repo / "elsewhere.py").write_text(IMPL_FIXED)
    (repo / "impl.py").unlink()
    (repo / "impl.py").symlink_to("elsewhere.py")
    result = run(repo, "test_impl.py::test_add", "impl.py")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "symlink" in result.stderr
    assert (repo / "impl.py").is_symlink()


def test_a_git_error_in_the_index_check_is_not_reported_as_staged(
    repo: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.py"
    outside.write_text("x = 1\n")
    result = run(repo, "test_impl.py::test_add", "impl.py", "../outside.py")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "in the index" not in result.stderr
    assert "outside repository" in result.stderr, result.stderr
