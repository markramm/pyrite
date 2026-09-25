"""The CI `verify-red` job and the script behind it (#352).

The review lane proves by hand that a PR's new tests fail without its fix
(`scripts/verify-red.sh`, review.md). `scripts/verify_red_ci.py` does it for
every pull request: it splits the PR's changed files into tests and
implementation, runs each changed test file with the implementation reverted
to the merge base, and classifies each test. It is also the one owner of the
revert and the restore (retro 10, #368): `verify-red.sh` is a wrapper over its
`--test` mode, so the stale-.pyc and wrong-tree guards are the same ones.

The properties the restore promises -- whatever ends the run, the files hold
their committed bytes and the index is untouched; an edit is never overwritten;
a restore that cannot complete is named file by file; checkout conversion and
non-UTF-8 files hold -- are pinned below on real repositories with the real
script.

It is a SIGNAL, not a gate: "passes without the fix" is a warning annotation,
and the job fails only on its own infrastructure errors. The last class in this
module pins the job's shape in `ci.yml` -- pull_request only, not in `gate`'s
needs, read-only, bounded -- the way `test_dev_process_config.py` pins the hooks.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import re
import signal
import subprocess
import sys
import time
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


def test_an_interrupted_session_is_not_a_collection_error(vr, tmp_path: Path) -> None:
    # pytest writes a bare <testcase/> when a session is interrupted or hits an
    # internal error; only a classname-less testcase WITH an <error> is a module
    # that failed to import.
    xml = tmp_path / "r.xml"
    xml.write_text('<testsuites><testsuite><testcase time="0.000" /></testsuite></testsuites>')
    assert not vr.read_junit(xml, "tests/test_x.py").collection_error
    xml.write_text(
        '<testsuites><testsuite><testcase classname="" name="test_x" file="tests/test_x.py">'
        '<error message="collection failure">ImportError</error></testcase>'
        "</testsuite></testsuites>"
    )
    assert vr.read_junit(xml, "tests/test_x.py").collection_error


def test_a_missing_report_is_an_infrastructure_error(vr, tmp_path: Path) -> None:
    with pytest.raises(vr.InfraError):
        vr.read_junit(tmp_path / "absent.xml", "tests/test_x.py")


MONKEYPATCH_TESTS = """\
import json
from unittest import mock

import pytest

import t_mp


@pytest.fixture
def patched_in_setup(monkeypatch):
    monkeypatch.setattr("json.nope_helper", 1)


def test_string_target(monkeypatch):
    monkeypatch.setattr("json.nope_helper", 1)


def test_class_target(monkeypatch):
    monkeypatch.setattr(t_mp.C, "helper", 1)


def test_module_object_target(monkeypatch):
    monkeypatch.setattr(json, "nope_helper", 1)


def test_module_attribute_read():
    json.nope_helper


def test_in_setup(patched_in_setup):
    pass


def test_class_attribute_read():
    t_mp.C.helper


def test_object_attribute_read():
    None.title


def test_mock_patch_string_target():
    with mock.patch("json.nope_helper", 1):
        pass


@mock.patch("json.nope_decorated")
def test_mock_patch_decorator(m):
    pass


def test_mock_patch_object_module():
    with mock.patch.object(json, "nope_helper", 1):
        pass


def test_mock_patch_object_class():
    with mock.patch.object(t_mp.C, "helper", 1):
        pass


def test_mock_patch_object_instance():
    with mock.patch.object(t_mp.C(), "helper", 1):
        pass


def test_delattr_module(monkeypatch):
    monkeypatch.delattr(json, "nope_helper")


def test_delattr_class(monkeypatch):
    monkeypatch.delattr(t_mp.C, "nope_helper")


def test_delattr_string_target(monkeypatch):
    monkeypatch.delattr("json.nope_helper")


class Lazy:
    def __getattr__(self, name):
        raise AttributeError(name)


def test_getattr_raising_the_bare_name():
    Lazy().title


def test_assertion_quoting_an_import_error():
    assert "ImportError: cannot import name 'x'" == "fixed"


def test_assertion_message_with_an_attribute_error_line():
    assert False, "context\\nAttributeError: module 'json' has no attribute 'x'"
"""


@pytest.fixture(scope="module")
def junit_attribute_errors(vr, tmp_path_factory) -> dict[str, tuple[tuple[str, str], str]]:
    """The failure messages the job actually parses: a real pytest run, its JUnit report."""
    d = tmp_path_factory.mktemp("attr")
    (d / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    (d / "t_mp.py").write_text("class C:\n    pass\n")
    (d / "test_mp.py").write_text(MONKEYPATCH_TESTS)
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_mp.py",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={d / 'r.xml'}",
            "-o",
            "junit_family=xunit1",
        ],
        cwd=d,
        env=env,
        capture_output=True,
    )
    report = vr.read_junit(d / "r.xml", "test_mp.py")
    return {
        nodeid.split("::")[-1]: (outcome, report.texts.get(nodeid, ""))
        for nodeid, outcome in report.outcomes.items()
    }


@pytest.mark.parametrize(
    ("test", "weak"),
    [
        ("test_string_target", True),  # 'module' object at json has no attribute
        ("test_class_target", True),  # <class 't_mp.C'> has no attribute
        ("test_module_object_target", True),  # <module 'json' ...> has no attribute
        ("test_module_attribute_read", True),  # module 'json' has no attribute
        ("test_in_setup", True),  # the same, raised in a fixture: an <error>
        ("test_class_attribute_read", False),  # type object 'C' has no attribute: behaviour
        ("test_object_attribute_read", False),  # 'NoneType' object has no attribute
        # unittest.mock: "<module ...> / <class ...> does not have the attribute"
        ("test_mock_patch_string_target", True),
        ("test_mock_patch_decorator", True),
        ("test_mock_patch_object_module", True),
        ("test_mock_patch_object_class", True),
        ("test_mock_patch_object_instance", False),  # an instance: behaviour, as above
        # monkeypatch.delattr of a name the fix adds: "AttributeError: <name>"
        ("test_delattr_module", True),
        ("test_delattr_class", True),
        ("test_delattr_string_target", True),
        # the same bare "AttributeError: title" from an object's __getattr__: behaviour
        ("test_getattr_raising_the_bare_name", False),
        # the exception is AssertionError: text quoted in its message is not the error
        ("test_assertion_quoting_an_import_error", False),
        ("test_assertion_message_with_an_attribute_error_line", False),
    ],
)
def test_attribute_errors_as_the_junit_report_carries_them(
    vr, junit_attribute_errors, test: str, weak: bool
) -> None:
    outcome, text = junit_attribute_errors[test]
    assert outcome[0] in ("failed", "error"), outcome
    label, _ = vr.classify(("passed", ""), outcome, collection_error=False, text=text)
    assert label == (vr.RED_IMPORT if weak else vr.RED), outcome


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


def run_ci(
    repo: Path, tmp_path: Path, *extra: str, env_extra: dict[str, str] | None = None
) -> tuple[subprocess.CompletedProcess[str], str]:
    summary = tmp_path / "summary.md"
    env = {
        **os.environ,
        "GITHUB_STEP_SUMMARY": str(summary),
        "VERIFY_RED_PYTHON": sys.executable,
        **(env_extra or {}),
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


def test_the_job_runs_from_a_subdirectory(vr, repo: Path, tmp_path: Path) -> None:
    _commit_fix(repo)
    summary = tmp_path / "summary.md"
    env = {**os.environ, "GITHUB_STEP_SUMMARY": str(summary), "VERIFY_RED_PYTHON": sys.executable}
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "dev"],
        cwd=repo / "tests",
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert vr.RED in row(summary.read_text(), "tests/test_add.py::test_real")
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


EDITS_DURING_THE_RUN = OLD_TESTS + (
    "\n\ndef test_real():\n"
    "    from pathlib import Path\n\n"
    "    impl = Path('pyrite/__init__.py')\n"
    "    if '# edited during the run' not in impl.read_text():\n"
    "        impl.write_text(impl.read_text() + '# edited during the run\\n')\n"
    "    assert add(2, 2) == 4\n"
)


def test_an_edit_made_during_the_run_survives_the_refusal(repo: Path, tmp_path: Path) -> None:
    # An editor autosave or another session changes an implementation file after
    # the up-front check. The reverted run refuses (uncommitted edits); nothing was
    # reverted, so nothing may be "restored" over the edit on the way out.
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(EDITS_DURING_THE_RUN)
    git(repo, "commit", "-q", "-am", "fix: add adds")
    result, _ = run_ci(repo, tmp_path)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "uncommitted" in result.stderr
    assert "# edited during the run" in (repo / "pyrite" / "__init__.py").read_text()


def _git_recording_checkouts(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """A `git` on PATH that fails, and counts, every `checkout`."""
    bin_dir, count = tmp_path / "bin", tmp_path / "checkouts"
    bin_dir.mkdir()
    count.write_text("0")
    wrapper = bin_dir / "git"
    wrapper.write_text(
        "#!/bin/sh\n"
        'for a in "$@"; do\n'
        '  if [ "$a" = checkout ]; then\n'
        f'    echo $(( $(cat "{count}") + 1 )) > "{count}"; exit 1\n'
        "  fi\n"
        "done\n"
        f'exec "{shutil.which("git")}" "$@"\n'
    )
    wrapper.chmod(0o755)
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}, count


def _commit_fix(repo: Path) -> None:
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    git(repo, "commit", "-q", "-am", "fix: add adds")


def _index(repo: Path) -> bytes:
    return (repo / ".git" / "index").read_bytes()


def test_git_checkout_is_never_what_restores(repo: Path, tmp_path: Path) -> None:
    # Replaces the two tests that pinned the old design, where verify-red.sh's
    # EXIT trap restored with `git checkout ... || true` and the driver checked
    # its work with a second, content-based restore (#357, three review rounds).
    # One owner now writes the files itself, so a `git checkout` that fails
    # (an index.lock held by an IDE) cannot touch the run at all.
    _commit_fix(repo)
    env, count = _git_recording_checkouts(tmp_path)
    result, summary = run_ci(repo, tmp_path, env_extra=env)
    assert count.read_text().strip() == "0", "the run used git checkout"
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "red without the fix" in summary
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED
    assert git(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("flavour", ["lf", "crlf", "latin-1"])
def test_the_index_is_never_written(vr, repo: Path, tmp_path: Path, flavour: str) -> None:
    # Property 1: the index after the run is the index before it, byte for byte --
    # so an interrupt can never strand .git/index.lock or a staged merge-base file.
    # Property 4: the verdict and the restore hold under checkout conversion and
    # for a file that is not UTF-8; the file comes back byte for byte.
    impl = repo / "pyrite" / "__init__.py"
    if flavour == "crlf":
        (repo / ".gitattributes").write_text("*.py text eol=crlf\n")
    impl.write_bytes(_encode(BROKEN, flavour))
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    fixed = _encode(FIXED, flavour)
    impl.write_bytes(fixed)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    git(repo, "commit", "-q", "-am", "fix: add adds")
    assert git(repo, "status", "--porcelain") == ""
    before = _index(repo)

    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert vr.RED in row(summary, "tests/test_add.py::test_real")
    assert _index(repo) == before
    assert not (repo / ".git" / "index.lock").exists()
    assert not (repo / JOURNAL).exists()
    assert impl.read_bytes() == fixed
    assert git(repo, "status", "--porcelain") == ""


def test_an_index_only_revert_is_refused_and_left_alone(repo: Path, tmp_path: Path) -> None:
    # #368 (5): the working file is at HEAD but the index holds the merge base.
    # That is uncommitted state: refused before anything runs, and left as found.
    _commit_fix(repo)
    git(repo, "checkout", "-q", "dev", "--", "pyrite/__init__.py")
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    staged = git(repo, "ls-files", "-s", "pyrite/__init__.py")
    before = _index(repo)
    result, _ = run_ci(repo, tmp_path)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "uncommitted" in result.stderr
    assert _index(repo) == before
    assert git(repo, "ls-files", "-s", "pyrite/__init__.py") == staged
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED


EDITS_TO_OTHER_FILES = OLD_TESTS + (
    "\n\ndef test_real():\n"
    "    from pathlib import Path\n\n"
    "    if add(2, 2) != 4:  # the reverted run\n"
    "        for f in ('pyrite/__init__.py', 'pyrite/other.py', 'README.md'):\n"
    "            Path(f).write_text(Path(f).read_text() + '# edited during the run\\n')\n"
    "    assert add(2, 2) == 4\n"
)


def test_edits_made_before_or_during_the_run_are_never_overwritten(
    repo: Path, tmp_path: Path
) -> None:
    # Property 2. Files the run did not revert (an unchanged implementation file,
    # a README with an uncommitted edit) keep every edit; a reverted file edited
    # during the run is left as the editor left it and reported, not "restored".
    (repo / "pyrite" / "other.py").write_text("X = 1\n")
    (repo / "README.md").write_text("readme\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(EDITS_TO_OTHER_FILES)
    git(repo, "commit", "-q", "-am", "fix: add adds")
    (repo / "README.md").write_text("readme\n# edited before the run\n")

    result, _ = run_ci(repo, tmp_path)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "pyrite/__init__.py" in result.stderr and "changed during the run" in result.stderr
    assert (repo / "pyrite" / "__init__.py").read_text() == BROKEN + "# edited during the run\n"
    assert (repo / "pyrite" / "other.py").read_text() == "X = 1\n# edited during the run\n"
    assert (repo / "README.md").read_text() == (
        "readme\n# edited before the run\n# edited during the run\n"
    )


PUT_BACK_DURING_THE_RUN = OLD_TESTS + (
    "\n\ndef test_real():\n"
    "    from pathlib import Path\n\n"
    "    if add(2, 2) != 4:  # the reverted run: someone puts the fix back\n"
    f"        Path('pyrite/__init__.py').write_text({FIXED!r})\n"
    "    assert add(2, 2) == 4\n"
)


def test_a_file_already_back_at_head_needs_no_restore(vr, repo: Path, tmp_path: Path) -> None:
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(PUT_BACK_DURING_THE_RUN)
    git(repo, "commit", "-q", "-am", "fix: add adds")
    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert vr.RED in row(summary, "tests/test_add.py::test_real")
    assert git(repo, "status", "--porcelain") == ""


SABOTAGE_TESTS = """\
import os
import time
from pathlib import Path

from pyrite.a.x import V as A
from pyrite.b.y import V as B
from pyrite.c.z import V as C


def test_v():
    if A == 1:  # the reverted run: make two of the three restores impossible
        Path("pyrite/b/y.py").chmod(0)
        Path("pyrite/a").chmod(0o555)
        Path({pidfile!r}).write_text(str(os.getpid()))
        if {hang}:
            time.sleep(120)
    assert (A, B, C) == (2, 2, 2)
"""


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores modes")
@pytest.mark.parametrize("ending", ["fails", "times out", "SIGTERM"])
def test_a_restore_that_cannot_complete_is_reported_file_by_file(
    repo: Path, tmp_path: Path, ending: str
) -> None:
    # Property 3 and #368 (2)-(4): the first file cannot be written, the second
    # cannot be read; both are named, the third is still restored, and the exit
    # is non-zero -- after a verdict, after a timeout (an ordinary exception in
    # flight) and after SIGTERM (which keeps its own exit status).
    for d in ("a", "b", "c"):
        (repo / "pyrite" / d).mkdir()
    for f in ("a/x.py", "b/y.py", "c/z.py"):
        (repo / "pyrite" / f).write_text("V = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    for f in ("a/x.py", "b/y.py", "c/z.py"):
        (repo / "pyrite" / f).write_text("V = 2\n")
    pidfile = tmp_path / "run.pid"
    (repo / "tests" / "test_v.py").write_text(
        SABOTAGE_TESTS.format(pidfile=str(pidfile), hang=ending != "fails")
    )
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: V is 2")

    env = {**os.environ, "VERIFY_RED_PYTHON": sys.executable}
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("GITHUB_STEP_SUMMARY", None)
    timeout = "5" if ending == "times out" else "100"
    try:
        driver = subprocess.Popen(
            [sys.executable, str(SCRIPT), "--base", "dev", "--timeout", timeout],
            cwd=repo,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if ending == "SIGTERM":
            deadline = time.monotonic() + 60
            while not (pidfile.exists() and pidfile.read_text().strip()):
                assert driver.poll() is None, driver.communicate()
                assert time.monotonic() < deadline, "the reverted run never started"
                time.sleep(0.1)
            driver.send_signal(signal.SIGTERM)
        _, err = driver.communicate(timeout=90)
    finally:
        (repo / "pyrite" / "a").chmod(0o755)
        (repo / "pyrite" / "b" / "y.py").chmod(0o644)
        if driver.poll() is None:
            driver.kill()

    expected = 128 + signal.SIGTERM if ending == "SIGTERM" else 2
    assert driver.returncode == expected, err
    assert "pyrite/a/x.py" in err, err
    assert "pyrite/b/y.py" in err, err
    assert (repo / "pyrite" / "c" / "z.py").read_text() == "V = 2\n"
    # The tree is not as committed: the next run must say so, not "commit them first".
    assert (repo / JOURNAL).exists()


SIGNAL_DURING_RESTORE = """\
import importlib.util
import os
import signal
import sys

spec = importlib.util.spec_from_file_location("verify_red_ci", {script!r})
vr = importlib.util.module_from_spec(spec)
sys.modules["verify_red_ci"] = vr
spec.loader.exec_module(vr)

real_put, calls = vr._put, []


def put(*args, **kwargs):
    real_put(*args, **kwargs)
    calls.append(args)
    if len(calls) == 3:  # two reverted, one restored: the second restore is next
        os.kill(os.getpid(), signal.SIGTERM)


vr._put = put
sys.exit(vr.main(["--base", "dev"]))
"""


def test_a_signal_during_the_restore_waits_for_it(repo: Path, tmp_path: Path) -> None:
    # A second Ctrl-C or a job cancellation arriving while the tree is being put
    # back must not leave the rest of it reverted: it is held until the restore ends.
    (repo / "pyrite" / "extra.py").write_text("E = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    (repo / "pyrite" / "extra.py").write_text("E = 2\n")
    _commit_fix(repo)
    script = tmp_path / "driver.py"
    script.write_text(SIGNAL_DURING_RESTORE.format(script=str(SCRIPT)))
    env = {**os.environ, "VERIFY_RED_PYTHON": sys.executable}
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("GITHUB_STEP_SUMMARY", None)
    result = subprocess.run(
        [sys.executable, str(script)], cwd=repo, env=env, capture_output=True, text=True
    )
    assert result.returncode == 128 + signal.SIGTERM, (result.stdout, result.stderr)
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED
    assert (repo / "pyrite" / "extra.py").read_text() == "E = 2\n"
    assert git(repo, "status", "--porcelain") == ""


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores modes")
def test_a_revert_that_cannot_write_is_refused_and_undone(repo: Path, tmp_path: Path) -> None:
    # The second file cannot be written (its directory is read-only): the run is
    # refused, and the first file, already reverted, is put back.
    (repo / "pyrite" / "ro").mkdir()
    (repo / "pyrite" / "ro" / "z.py").write_text("Z = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    (repo / "pyrite" / "ro" / "z.py").write_text("Z = 2\n")
    _commit_fix(repo)
    (repo / "pyrite" / "ro").chmod(0o555)
    try:
        result, _ = run_ci(repo, tmp_path)
    finally:
        (repo / "pyrite" / "ro").chmod(0o755)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "pyrite/ro/z.py: not reverted" in result.stderr
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED
    assert git(repo, "status", "--porcelain") == ""


def test_a_write_that_fails_leaves_no_temporary_file(vr, tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "f.py"
    target.write_text("old\n")

    def refuse(*args):
        raise OSError("no")

    monkeypatch.setattr(vr.os, "replace", refuse)
    with pytest.raises(OSError):
        vr._put(str(target), b"new\n", 0o644)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["f.py"]
    assert target.read_text() == "old\n"


SIGINT_BEFORE_THE_MASK = """\
import importlib.util
import os
import signal
import sys
from contextlib import contextmanager

spec = importlib.util.spec_from_file_location("verify_red_ci", {script!r})
vr = importlib.util.module_from_spec(spec)
sys.modules["verify_red_ci"] = vr
spec.loader.exec_module(vr)

real_held, fired = vr._signals_held, []


@contextmanager
def held():
    # A second Ctrl-C whose Python handler is pending as the restore begins --
    # before the signal mask is up. It runs at the next bytecode check: here.
    if not fired:
        fired.append(1)
        os.kill(os.getpid(), signal.SIGINT)
        for _ in range(1000):
            pass
    with real_held():
        yield


vr._signals_held = held
sys.exit(vr.main(["--base", "dev"]))
"""


def test_a_ctrl_c_pending_as_the_restore_begins_does_not_skip_it(
    repo: Path, tmp_path: Path
) -> None:
    (repo / "pyrite" / "extra.py").write_text("E = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    (repo / "pyrite" / "extra.py").write_text("E = 2\n")
    _commit_fix(repo)
    script = tmp_path / "driver.py"
    script.write_text(SIGINT_BEFORE_THE_MASK.format(script=str(SCRIPT)))
    env = {**os.environ, "VERIFY_RED_PYTHON": sys.executable}
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("GITHUB_STEP_SUMMARY", None)
    result = subprocess.run(
        [sys.executable, str(script)], cwd=repo, env=env, capture_output=True, text=True
    )
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "KeyboardInterrupt" in result.stderr, result.stderr  # the Ctrl-C still ends the run
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED
    assert (repo / "pyrite" / "extra.py").read_text() == "E = 2\n"
    assert git(repo, "status", "--porcelain") == ""


JOURNAL = Path(".git") / "verify-red.inflight"


def test_a_run_after_the_driver_was_killed_says_so(repo: Path, tmp_path: Path) -> None:
    # SIGKILL (the OOM killer) cannot be caught: the merge-base code stays on disk.
    # The next run must not say "uncommitted changes; commit them first" -- that
    # would commit the merge base over the fix -- but name the files and the way back.
    pidfile, hang = tmp_path / "hung.pid", tmp_path / "hang"
    hang.touch()
    (repo / "pyrite" / "__init__.py").write_text(
        "import os\nimport time\n\n\ndef add(a, b):\n"
        f"    if os.path.exists({str(hang)!r}):\n"
        f"        open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
        "        time.sleep(120)\n"
        "    return a - b\n"
    )
    git(repo, "commit", "-q", "--amend", "-am", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    _commit_fix(repo)
    env = {**os.environ, "VERIFY_RED_PYTHON": sys.executable}
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("GITHUB_STEP_SUMMARY", None)
    driver = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--base", "dev"],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 60
        while not (pidfile.exists() and pidfile.read_text().strip()):
            assert driver.poll() is None, "the driver exited before the run hung"
            assert time.monotonic() < deadline, "the reverted run never started"
            time.sleep(0.1)
        driver.kill()
        driver.wait(timeout=30)
    finally:
        if driver.poll() is None:
            driver.kill()
        if pidfile.exists() and pidfile.read_text().strip():
            try:
                os.kill(int(pidfile.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
    assert (repo / "pyrite" / "__init__.py").read_text() != FIXED  # left reverted

    result, _ = run_ci(repo, tmp_path)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "did not finish restoring" in result.stderr, result.stderr
    assert "pyrite/__init__.py" in result.stderr
    assert "commit them first" not in result.stderr

    # The way back it names works.
    hang.unlink()
    git(repo, "checkout", "HEAD", "--", "pyrite/__init__.py")
    (repo / JOURNAL).unlink()
    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "red without the fix" in summary
    assert not (repo / JOURNAL).exists()


def test_a_killed_run_leaves_the_tree_restored(vr, repo: Path, tmp_path: Path) -> None:
    # The reverted pytest is SIGKILLed (the OOM killer): no report, a row, and the
    # tree and index exactly as before.
    (repo / "pyrite" / "__init__.py").write_text(
        "import os\nimport signal\n\n\ndef add(a, b):\n    os.kill(os.getpid(), signal.SIGKILL)\n"
    )
    git(repo, "commit", "-q", "--amend", "-am", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    _commit_fix(repo)
    before = _index(repo)
    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    line = row(summary, "tests/test_add.py")
    assert vr.NOT_VERIFIABLE in line and "no report without the fix" in line, line
    assert (repo / "pyrite" / "__init__.py").read_text() == FIXED
    assert _index(repo) == before


def test_a_refusal_leaves_a_staged_revert_alone(repo: Path, tmp_path: Path) -> None:
    # A developer checking red by hand has the merge-base code staged. The driver
    # refuses ("commit them first") before running anything, and must leave that
    # state exactly as it found it -- not "restore" the fix over it.
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    git(repo, "commit", "-q", "-am", "fix: add adds")
    git(repo, "checkout", "-q", "dev", "--", "pyrite/__init__.py")
    result, _ = run_ci(repo, tmp_path)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "uncommitted" in result.stderr
    assert (repo / "pyrite" / "__init__.py").read_text() == BROKEN
    assert git(repo, "status", "--porcelain") == "M  pyrite/__init__.py"


def test_a_non_utf8_implementation_file_is_compared_as_bytes(repo: Path, tmp_path: Path) -> None:
    impl = repo / "pyrite" / "__init__.py"
    impl.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\n" + FIXED.encode())
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    git(repo, "commit", "-q", "-am", "fix: add adds")
    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "red without the fix" in summary
    assert impl.read_bytes().startswith(b"# -*- coding: latin-1")
    assert git(repo, "status", "--porcelain") == ""


PINNED_MTIME = 1_700_000_000


def _pin_mtimes(repo: Path) -> None:
    """Every checkout leaves every .py at ONE mtime -- the worst case for bytecode.

    CPython validates a .pyc by the source's mtime (whole seconds) and size. A
    revert and a restore inside the same second, between two sources of the same
    size, is what the cold read hit; pinning the mtime makes it happen every run
    instead of most runs. (The driver now writes the files itself, so the hook
    fires only if a restore ever goes back to `git checkout`; the bytecode guard
    itself is pinned by test_verify_red.py::test_stale_bytecode_is_not_served_...)
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


GONE_TESTS = """\
import pytest


def test_the_legacy_package_is_gone():
    with pytest.raises(ImportError):
        import pyrite.legacy  # noqa: F401
"""


def test_a_deleted_package_leaves_no_directory_behind(vr, repo: Path, tmp_path: Path) -> None:
    # The revert recreates pyrite/legacy/ to put the merge base's files back; the
    # restore removes the files AND the directories it made. An empty directory
    # left behind imports as a namespace package, so the next file's run with
    # the fix saw a package the PR deleted.
    (repo / "pyrite" / "legacy" / "sub").mkdir(parents=True)
    (repo / "pyrite" / "legacy" / "__init__.py").write_text("")
    (repo / "pyrite" / "legacy" / "core.py").write_text("X = 1\n")
    (repo / "pyrite" / "legacy" / "sub" / "deep.py").write_text("Y = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    git(repo, "rm", "-q", "-r", "pyrite/legacy")
    (repo / "tests" / "test_gone_a.py").write_text(GONE_TESTS)
    (repo / "tests" / "test_gone_b.py").write_text(GONE_TESTS)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: drop the legacy package")
    assert not (repo / "pyrite" / "legacy").exists()

    result, summary = run_ci(repo, tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    for f in ("test_gone_a", "test_gone_b"):
        assert vr.RED in row(summary, f"tests/{f}.py::test_the_legacy_package_is_gone"), summary
    assert not (repo / "pyrite" / "legacy").exists()
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


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _encode(text: str, flavour: str) -> bytes:
    """A source file as a checkout of that flavour holds it on disk."""
    if flavour == "crlf":
        return text.replace("\n", "\r\n").encode()
    if flavour == "latin-1":
        return b"# -*- coding: latin-1 -*-\n# caf\xe9\n" + text.encode()
    return text.encode()


@pytest.mark.parametrize(
    ("sig", "flavour"),
    [
        pytest.param(sig, flavour, id=f"{sig.name}-{flavour}")
        for sig in (signal.SIGINT, signal.SIGTERM)
        for flavour in ("lf", "crlf", "latin-1")
    ]
    # The terminal closing (SSH dropped) and Ctrl-\: the wrapper execs the driver,
    # so no bash EXIT trap stands behind it any more.
    + [pytest.param(sig, "lf", id=f"{sig.name}-lf") for sig in (signal.SIGHUP, signal.SIGQUIT)],
)
def test_interrupting_the_driver_restores_the_tree_and_kills_the_run(
    repo: Path, tmp_path: Path, sig: signal.Signals, flavour: str
) -> None:
    # The reverted `add` records its pid and hangs, so the signal lands while the
    # tree is reverted and pytest is running in its own session. Property 1 on
    # the interrupt path, and property 4: under `*.py text eol=crlf` a checkout
    # writes CRLF while the blob holds LF (#368 (1): a byte compare against the
    # blob skipped the restore), and a latin-1 file is bytes, not text.
    pidfile = tmp_path / "hung.pid"
    impl = repo / "pyrite" / "__init__.py"
    if flavour == "crlf":
        (repo / ".gitattributes").write_text("*.py text eol=crlf\n")
    impl.write_bytes(
        _encode(
            "import os\nimport time\n\n\ndef add(a, b):\n"
            f"    open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "    time.sleep(120)\n    return a - b\n",
            flavour,
        )
    )
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--amend", "-m", "base")
    git(repo, "branch", "-f", "dev", "HEAD")
    fixed = _encode(FIXED, flavour)
    impl.write_bytes(fixed)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: add adds, promptly")
    assert git(repo, "status", "--porcelain") == ""
    before = _index(repo)

    env = {**os.environ, "VERIFY_RED_PYTHON": sys.executable}
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("GITHUB_STEP_SUMMARY", None)
    driver = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--base", "dev", "--timeout", "100"],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 60
        while not (pidfile.exists() and pidfile.read_text().strip()):
            assert driver.poll() is None, "the driver exited before the run hung"
            assert time.monotonic() < deadline, "the reverted run never started"
            time.sleep(0.1)
        hung = int(pidfile.read_text())
        assert impl.read_bytes() != fixed  # reverted right now

        driver.send_signal(sig)
        driver.wait(timeout=30)
    finally:
        if driver.poll() is None:
            driver.kill()

    assert driver.returncode != 0
    deadline = time.monotonic() + 10
    while _alive(hung) and time.monotonic() < deadline:
        time.sleep(0.1)
    alive = _alive(hung)
    if alive:
        os.kill(hung, signal.SIGKILL)
    assert not alive, "the pytest run outlived the driver"
    assert impl.read_bytes() == fixed
    assert _index(repo) == before
    assert not (repo / ".git" / "index.lock").exists()
    assert git(repo, "status", "--porcelain") == ""


class TestRunTimeout:
    """Each run gets the per-run timeout, cut to what the budget has left once the
    kill grace is set aside; too little left, and the run is not started."""

    def test_no_budget_is_the_per_run_timeout(self, vr):
        assert vr.run_timeout(120, None) == 120

    def test_plenty_left_is_the_per_run_timeout(self, vr):
        assert vr.run_timeout(120, 1000) == 120

    def test_the_kill_grace_is_set_aside(self, vr):
        assert vr.run_timeout(120, vr.KILL_GRACE + 30) == 30

    def test_too_little_left_is_no_run(self, vr):
        assert vr.run_timeout(120, vr.KILL_GRACE + vr.MIN_RUN - 1) is None


def test_a_spent_budget_turns_every_remaining_file_into_a_row(
    vr, repo: Path, tmp_path: Path
) -> None:
    (repo / "pyrite" / "__init__.py").write_text(FIXED)
    (repo / "tests" / "test_add.py").write_text(PR_TESTS)
    (repo / "tests" / "test_helper.py").write_text(NEW_FILE_TESTS)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "fix: add adds")

    result, summary = run_ci(repo, tmp_path, "--budget", "0")
    assert result.returncode == 0, (result.stdout, result.stderr)
    for f in ("tests/test_add.py", "tests/test_helper.py"):
        line = row(summary, f)
        assert vr.NOT_VERIFIABLE in line and "time budget" in line, line
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
        assert 0 < job["timeout-minutes"] <= 30

    def test_the_script_budget_ends_before_the_job_is_cancelled(self, ci):
        # A cancelled job loses the summary's legend and any file not yet
        # written; a spent budget turns the remaining files into rows instead.
        job = ci["jobs"]["verify-red"]
        run = "\n".join(s.get("run", "") for s in job["steps"])
        m = re.search(r"--budget (\d+)", run)
        assert m, "the job must pass --budget"
        install_margin = 5 * 60  # checkout, Python, uv, the editable installs
        assert int(m.group(1)) + install_margin <= job["timeout-minutes"] * 60

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


def test_review_md_does_not_trust_a_table_the_pr_itself_can_rewrite():
    # The job runs the PR's own copy of the script and the workflow: a PR that
    # changes either produces a table the review cannot take on trust.
    review = (REPO / ".claude" / "skills" / "pyrite-conductor" / "review.md").read_text()
    text = " ".join(review.split())
    assert "the PR itself touches `scripts/verify*red*` or the `verify-red` job" in text
