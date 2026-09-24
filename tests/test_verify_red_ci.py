"""The CI `verify-red` job and the script behind it (#352).

The review lane proves by hand that a PR's new tests fail without its fix
(`scripts/verify-red.sh`, review.md). `scripts/verify_red_ci.py` does it for
every pull request: it splits the PR's changed files into tests and
implementation, runs each changed test file with the implementation reverted
to the merge base (through `verify-red.sh`, so the revert/restore, stale-.pyc
and wrong-tree guards are the same ones), and classifies each test.

It is a SIGNAL, not a gate: "passes without the fix" is a warning annotation,
and the job fails only on its own infrastructure errors. The last class in this
module pins the job's shape in `ci.yml` -- pull_request only, not in `gate`'s
needs, read-only, bounded -- the way `test_dev_process_config.py` pins the hooks.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "verify_red_ci.py"
CI_PATH = REPO / ".github" / "workflows" / "ci.yml"


def _load():
    spec = importlib.util.spec_from_file_location("verify_red_ci", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_red_ci"] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def vr():
    return _load()


# ---------------------------------------------------------------------------
# Pure decisions: which files are tests, which tests the PR touched, and how a
# pair of runs (with the fix, without it) classifies a test.
# ---------------------------------------------------------------------------


class TestSplitChangedFiles:
    def test_tests_and_implementation_are_separated(self, vr):
        tests, impl = vr.split_changed(
            [
                "pyrite/services/kb_service.py",
                "tests/test_kb_service.py",
                "tests/unit/test_nested.py",
                "extensions/cascade/src/pyrite_cascade/plugin.py",
                "extensions/cascade/tests/test_plugin.py",
                "tests/conftest.py",  # not a test module: nothing to run
                "tests/fixtures/data.py",  # nor this
                "scripts/release.py",  # neither side
                "kb/backlog/x.md",
                "pyrite/static/app.css",  # not Python
                "extensions/cascade/pyproject.toml",
            ]
        )
        assert tests == [
            "extensions/cascade/tests/test_plugin.py",
            "tests/test_kb_service.py",
            "tests/unit/test_nested.py",
        ]
        assert impl == [
            "extensions/cascade/src/pyrite_cascade/plugin.py",
            "pyrite/services/kb_service.py",
        ]

    def test_nothing_on_either_side(self, vr):
        assert vr.split_changed(["README.md", "kb/x.md"]) == ([], [])


class TestWhichTestsThePRTouched:
    BASE = (
        "def test_old():\n    assert 1\n\n\n"
        "def test_edited():\n    assert 1\n\n\n"
        "class TestK:\n    def test_m(self):\n        assert 1\n\n\n"
        "def helper():\n    return 1\n"
    )
    HEAD = (
        "# a comment and reformatting do not make a test 'changed'\n"
        "def test_old():\n    assert  1\n\n\n"
        "def test_edited():\n    assert 2\n\n\n"
        "class TestK:\n    def test_m(self):\n        assert 1\n\n"
        "    def test_new_method(self):\n        assert 1\n\n\n"
        "def test_new():\n    assert 1\n\n\n"
        "def helper():\n    return 2\n"
    )

    def test_new_and_edited_tests_only(self, vr):
        assert vr.touched_tests(self.BASE, self.HEAD) == {
            ("test_edited",),
            ("TestK", "test_new_method"),
            ("test_new",),
        }

    def test_a_file_new_in_the_pr_touches_every_test(self, vr):
        assert vr.touched_tests(None, self.HEAD) == {
            ("test_old",),
            ("test_edited",),
            ("TestK", "test_m"),
            ("TestK", "test_new_method"),
            ("test_new",),
        }

    def test_a_decorator_change_is_a_change(self, vr):
        base = "def test_p(x):\n    assert x\n"
        head = (
            "import pytest\n\n\n@pytest.mark.parametrize('x', [1])\ndef test_p(x):\n    assert x\n"
        )
        assert vr.touched_tests(base, head) == {("test_p",)}

    def test_a_base_that_does_not_parse_counts_as_absent(self, vr):
        assert vr.touched_tests("def (:\n", "def test_a():\n    pass\n") == {("test_a",)}


class TestClassify:
    P = ("passed", "")

    def test_red_without_the_fix(self, vr):
        label, _ = vr.classify(self.P, ("failed", "assert 3 == 4"), collection_error=False)
        assert label == vr.RED

    def test_an_import_error_is_a_weak_red(self, vr):
        for msg in (
            "ImportError: cannot import name 'x' from 'pyrite.a'",
            "ModuleNotFoundError: No module named 'pyrite.new_module'",
        ):
            label, _ = vr.classify(self.P, ("failed", msg), collection_error=False)
            assert label == vr.RED_IMPORT, msg

    def test_a_missing_module_attribute_is_a_weak_red(self, vr):
        # monkeypatch.setattr on a name the fix adds, in a fixture or the body.
        for state, msg in (
            (
                "error",
                "failed on setup with \"AttributeError: <module 'pyrite.a' from "
                "'/x/pyrite/a.py'> has no attribute '_loop'\"",
            ),
            ("failed", "AttributeError: module 'pyrite.a' has no attribute 'new_helper'"),
        ):
            label, _ = vr.classify(self.P, (state, msg), collection_error=False)
            assert label == vr.RED_IMPORT, msg

    def test_an_attribute_error_on_an_object_is_a_real_red(self, vr):
        msg = "AttributeError: 'NoneType' object has no attribute 'title'"
        label, _ = vr.classify(self.P, ("failed", msg), collection_error=False)
        assert label == vr.RED

    def test_a_collection_error_is_a_weak_red_for_every_test_in_the_file(self, vr):
        label, _ = vr.classify(self.P, None, collection_error=True)
        assert label == vr.RED_IMPORT

    def test_passes_without_the_fix(self, vr):
        label, _ = vr.classify(self.P, self.P, collection_error=False)
        assert label == vr.PASSES

    def test_a_test_that_does_not_pass_with_the_fix_proves_nothing(self, vr):
        for head in (("failed", "boom"), ("skipped", "no postgres"), ("error", "fixture")):
            label, _ = vr.classify(head, ("failed", "x"), collection_error=False)
            assert label == vr.NOT_VERIFIABLE, head

    def test_skipped_without_the_fix_proves_nothing(self, vr):
        label, _ = vr.classify(self.P, ("skipped", "x"), collection_error=False)
        assert label == vr.NOT_VERIFIABLE


def test_junit_node_ids_keep_classes_and_parameters(vr, tmp_path: Path) -> None:
    xml = tmp_path / "r.xml"
    xml.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="extensions.x.tests.test_y.TestA.TestB" name="test_p[1-a]" />'
        '<testcase classname="extensions.x.tests.test_y" name="test_f">'
        '<failure message="assert 1 == 2">tb</failure></testcase>'
        '<testcase classname="x.tests.test_y" name="test_s"><skipped message="pg" /></testcase>'
        "</testsuite></testsuites>"
    )
    report = vr.read_junit(xml, "extensions/x/tests/test_y.py")
    assert report.outcomes == {
        "extensions/x/tests/test_y.py::TestA::TestB::test_p[1-a]": ("passed", ""),
        "extensions/x/tests/test_y.py::test_f": ("failed", "assert 1 == 2"),
        # a different rootdir shortens the dotted prefix; the node id is the same shape
        "extensions/x/tests/test_y.py::test_s": ("skipped", "pg"),
    }
    assert report.keys["extensions/x/tests/test_y.py::TestA::TestB::test_p[1-a]"] == (
        "TestA",
        "TestB",
        "test_p",
    )
    assert not report.collection_error


def test_a_missing_report_is_an_infrastructure_error(vr, tmp_path: Path) -> None:
    with pytest.raises(vr.InfraError):
        vr.read_junit(tmp_path / "absent.xml", "tests/test_x.py")


# ---------------------------------------------------------------------------
# End to end against a real repository: a base commit with a broken
# implementation in `pyrite/`, a PR branch that fixes it and adds tests.
# ---------------------------------------------------------------------------

BROKEN = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n\n\ndef helper():\n    return 1\n"
OLD_TESTS = "from pyrite import add\n\n\ndef test_unchanged():\n    assert add(0, 0) == 0\n"
PR_TESTS = OLD_TESTS + (
    "\n\ndef test_real():\n    assert add(2, 2) == 4\n"
    "\n\ndef test_vacuous():\n    assert callable(add)\n"
    "\n\ndef test_lazy_import():\n    from pyrite import helper\n\n    assert helper() == 1\n"
)
NEW_FILE_TESTS = "from pyrite import helper\n\n\ndef test_helper():\n    assert helper() == 1\n"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    (r / "pyrite").mkdir(parents=True)
    (r / "tests").mkdir()
    git(r, "init", "-q", "-b", "dev")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    (r / ".gitignore").write_text("__pycache__/\n*.xml\n")
    # pythonpath=. so the tests import THIS tree's `pyrite`, not the installed one.
    (r / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    (r / "pyrite" / "__init__.py").write_text(BROKEN)
    (r / "tests" / "test_add.py").write_text(OLD_TESTS)
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "base")
    git(r, "checkout", "-q", "-b", "fix/add")
    return r


def run_ci(repo: Path, tmp_path: Path, *extra: str) -> tuple[subprocess.CompletedProcess[str], str]:
    summary = tmp_path / "summary.md"
    env = {
        **os.environ,
        "GITHUB_STEP_SUMMARY": str(summary),
        "VERIFY_RED_PYTHON": sys.executable,
    }
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "dev", *extra],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    return result, summary.read_text() if summary.exists() else ""


def row(summary: str, test: str) -> str:
    lines = [ln for ln in summary.splitlines() if ln.startswith(f"| `{test}`")]
    assert len(lines) == 1, (test, summary)
    return lines[0]


def test_a_pr_is_classified_test_by_test(vr, repo: Path, tmp_path: Path) -> None:
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    (repo / "tests" / "test_helper.py").write_text(NEW_FILE_TESTS)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: add adds")

    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)

    assert vr.RED in row(summary, "tests/test_add.py::test_real")
    assert vr.PASSES in row(summary, "tests/test_add.py::test_vacuous")
    assert vr.RED_IMPORT in row(summary, "tests/test_add.py::test_lazy_import")
    assert vr.RED_IMPORT in row(summary, "tests/test_helper.py::test_helper")
    # The unchanged test is reported apart from the PR's own tests, and never warned about.
    assert "<details>" in summary
    assert "tests/test_add.py::test_unchanged" in summary.split("<details>", 1)[1]

    warnings = [ln for ln in result.stdout.splitlines() if ln.startswith("::warning")]
    assert len(warnings) == 1, result.stdout
    assert "tests/test_add.py::test_vacuous" in warnings[0]
    assert "file=tests/test_add.py" in warnings[0]

    # The tree is exactly as it was: the fix is back, nothing is left over.
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED
    assert git(repo, "status", "--porcelain") == ""


def test_no_implementation_change_is_nothing_to_verify(repo: Path, tmp_path: Path) -> None:
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    git(repo, "commit", "-q", "-am", "test: more tests")
    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, result.stderr
    assert "nothing to verify" in summary
    assert "::warning" not in result.stdout


def test_no_test_change_is_nothing_to_verify(repo: Path, tmp_path: Path) -> None:
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    git(repo, "commit", "-q", "-am", "refactor")
    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, result.stderr
    assert "nothing to verify" in summary
    # Implementation changed and no test did: worth a warning on the PR.
    warnings = [ln for ln in result.stdout.splitlines() if ln.startswith("::warning")]
    assert len(warnings) == 1, result.stdout
    assert "no test file" in warnings[0]


def test_an_infrastructure_error_fails_the_job(repo: Path, tmp_path: Path) -> None:
    # An uncommitted edit to the implementation: verify-red.sh refuses to make
    # a claim (exit 2). That is the job's own failure, not a verdict on the PR.
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    git(repo, "commit", "-q", "-am", "fix: add adds")
    (repo / "pyrite" / "__init__.py").write_text(FIXED + "# wip\n")
    result, _ = run_ci(repo, tmp_path)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "uncommitted" in result.stderr
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED + "# wip\n"


PINNED_MTIME = 1_700_000_000


def _pin_mtimes(repo: Path) -> None:
    """Every checkout leaves every .py at ONE mtime -- the worst case for bytecode.

    CPython validates a .pyc by the source's mtime (whole seconds) and size. A
    revert and a restore inside the same second, between two sources of the same
    size, is what the cold read hit; pinning the mtime makes it happen every run
    instead of most runs.
    """
    hook = repo / ".git" / "hooks" / "post-checkout"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        f'exec "{sys.executable}" -c "import os, pathlib\n'
        "for f in pathlib.Path('.').rglob('*.py'):\n"
        f"    '.git' in f.parts or os.utime(f, ({PINNED_MTIME}, {PINNED_MTIME}))\"\n"
    )
    hook.chmod(0o755)
    for f in repo.rglob("*.py"):
        os.utime(f, (PINNED_MTIME, PINNED_MTIME))


SAME_SIZE_FIX = "def add(a, b):\n    return a + b\n"  # same size as BROKEN


def test_a_same_size_fix_leaves_no_stale_bytecode(vr, repo: Path, tmp_path: Path) -> None:
    (repo / "pyrite" / "__init__.py").write_text(SAME_SIZE_FIX)
    real = "from pyrite import add\n\n\ndef test_real():\n    assert add(2, 2) == 4\n"
    (repo / "tests" / "test_a.py").write_text(real)
    (repo / "tests" / "test_b.py").write_text(real)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: add adds")
    _pin_mtimes(repo)

    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    # The second file's with-fix run must see the fix, not the reverted bytecode.
    assert vr.RED in row(summary, "tests/test_a.py::test_real")
    assert vr.RED in row(summary, "tests/test_b.py::test_real")
    # And the tree left behind runs the fix.
    out = subprocess.run(
        [sys.executable, "-c", "from pyrite import add; print(add(2, 2))"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert out == "4"


def test_a_file_with_no_report_without_the_fix_is_a_row(vr, repo: Path, tmp_path: Path) -> None:
    # A conftest that imports a name the fix adds: without the fix pytest cannot
    # even load it, and writes no report. That file gets a row; the table survives.
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "conftest.py").write_text("from pyrite import helper  # noqa: F401\n")
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    (repo / "tests" / "test_helper.py").write_text(NEW_FILE_TESTS)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: add adds")

    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    for f in ("tests/test_add.py", "tests/test_helper.py"):
        line = row(summary, f)
        assert vr.NOT_VERIFIABLE in line and "no report without the fix" in line, line
    assert git(repo, "status", "--porcelain") == ""


def test_renamed_and_deleted_implementation_is_reverted_and_restored(
    vr, repo: Path, tmp_path: Path
) -> None:
    body = "".join(f"\n\ndef unused_{i}():\n    return {i}\n" for i in range(20))
    (repo / "pyrite" / "calc.py").write_text("def add(a, b):\n    return a - b\n" + body)
    (repo / "pyrite" / "legacy.py").write_text("def add(a, b):\n    return a + b\n")
    (repo / "pyrite" / "__init__.py").write_text("from pyrite.calc import add  # noqa: F401\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")

    git(repo, "mv", "pyrite/calc.py", "pyrite/arith.py")
    (repo / "pyrite" / "arith.py").write_text("def add(a, b):\n    return a + b\n" + body)
    git(repo, "rm", "-q", "pyrite/legacy.py")
    (repo / "pyrite" / "__init__.py").write_text("from pyrite.arith import add  # noqa: F401\n")
    (repo / "tests" / "test_add.py").write_text(
        PR_TESTS.replace("from pyrite import helper", "from pyrite import add as helper")
    )
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: rename calc to arith, drop legacy")
    assert "R" in git(repo, "diff", "--name-status", "-M", "dev", "HEAD")  # git sees a rename

    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert vr.RED in row(summary, "tests/test_add.py::test_real")
    assert "`pyrite/calc.py`" in summary and "`pyrite/legacy.py`" in summary
    # Restored exactly: the renamed-away and deleted files are gone again.
    assert not (repo / "pyrite" / "calc.py").exists()
    assert not (repo / "pyrite" / "legacy.py").exists()
    assert (repo / "pyrite" / "arith.py").exists()
    assert git(repo, "status", "--porcelain") == ""


def test_a_hung_file_is_a_row_not_a_killed_job(vr, repo: Path, tmp_path: Path) -> None:
    (repo / "pyrite" / "__init__.py").write_text(
        "import time\n\n\ndef add(a, b):\n    time.sleep(60)\n    return a - b\n"
    )
    git(repo, "commit", "-q", "--amend", "-am", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    (repo / "tests" / "test_helper.py").write_text(NEW_FILE_TESTS)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: add adds, promptly")

    result, summary = run_ci(repo, tmp_path, "--timeout", "5")
    assert result.returncode == 0, (result.stdout, result.stderr)
    line = row(summary, "tests/test_add.py")
    assert vr.NOT_VERIFIABLE in line and "timed out without the fix" in line, line
    # The next file still ran.
    assert vr.RED_IMPORT in row(summary, "tests/test_helper.py::test_helper")
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED
    assert git(repo, "status", "--porcelain") == ""


# ---------------------------------------------------------------------------
# The job's shape in ci.yml.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ci() -> dict:
    return yaml.safe_load(CI_PATH.read_text())


class TestTheJobsShape:
    def test_it_exists(self, ci):
        assert "verify-red" in ci["jobs"]

    def test_it_runs_on_pull_request_only(self, ci):
        condition = ci["jobs"]["verify-red"]["if"]
        assert "github.event_name == 'pull_request'" in condition, condition
        assert "||" not in condition, f"another event could reach it: {condition}"

    def test_it_is_not_a_gate(self, ci):
        assert "verify-red" not in ci["jobs"]["gate"]["needs"]
        assert not ci["jobs"]["verify-red"].get("continue-on-error"), (
            "not needed: the job only fails on its own infrastructure errors, and it is not in gate"
        )

    def test_it_is_read_only(self, ci):
        assert ci["jobs"]["verify-red"].get("permissions") == {"contents": "read"}

    def test_it_is_bounded(self, ci):
        job = ci["jobs"]["verify-red"]
        assert 0 < job["timeout-minutes"] <= 15

    def test_it_runs_the_script_against_the_pr_base(self, ci):
        job = ci["jobs"]["verify-red"]
        run = "\n".join(step.get("run", "") for step in job["steps"])
        assert "scripts/verify_red_ci.py" in run
        assert "github.event.pull_request.base.sha" in run
        checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout"))
        assert checkout.get("with", {}).get("fetch-depth") == 0, "the merge base must be in history"

    def test_extensions_are_installed_editable_from_the_pr_tree(self, ci):
        # #189: the revert happens in the checkout, so imports must resolve
        # there -- an editable install of the PR tree, reverted in place.
        run = "\n".join(s.get("run", "") for s in ci["jobs"]["verify-red"]["steps"])
        assert 'install --system -e ".[all]"' in run
        assert 'uv pip install --system -e "$ext"' in run
