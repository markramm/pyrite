#!/usr/bin/env python3
"""Do a pull request's tests fail without its fix? The CI `verify-red` job (#352).

    python scripts/verify_red_ci.py --base <base ref or sha>

Splits the changes since the merge base with ``--base`` into test files
(``tests/**/test_*.py``, ``extensions/*/tests/**/test_*.py``) and
implementation (``.py`` under ``pyrite/`` and ``extensions/*/src/``). For each
changed test file it runs the file twice: once as committed, and once through
``scripts/verify-red.sh`` with every implementation file reverted to the merge
base. The revert, the restore, the stale-``.pyc`` guard and the wrong-tree
guard (#121, #189) are that script's; this one only chooses what to run and
reads the two JUnit reports. Each test is classified:

- **red without the fix** -- it failed on an assertion or error of its own:
  the evidence the review lane asks for.
- **red by import/collection error** -- it failed because a name the fix adds
  does not exist yet. Weak: it proves the test needs the new code, not that it
  checks what the code does.
- **passes without the fix** -- it does not test the change. A warning
  annotation on the PR, for a test the PR adds or edits; never a failure.
- **not verifiable** -- it did not pass with the fix (skipped, failed), was
  skipped without it, or its file timed out (``--timeout``, 120 s per run) or
  produced no report (a conftest importing a name the fix adds). No claim
  either way; the other files still run.

Implementation paths include the old side of a rename and deleted files, so
the reverted run sees the merge base's layout and the restore puts the PR's
back. Both runs set PYTHONDONTWRITEBYTECODE (see ``_RUN_ENV``).

Tests the PR did not add or edit (compared by AST, so formatting does not
count) are listed separately and never warned about.

The table goes to ``$GITHUB_STEP_SUMMARY`` (and stdout) one file at a time, so
a job killed part-way keeps what it found. A PR that changes implementation but
no test file gets a warning. Exit 0 whatever the verdicts; exit 2 only when the
check itself could not run -- verify-red.sh refused, git failed, the tree was
not restored. It is a signal, not a gate.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

RED = "red without the fix"
RED_IMPORT = "red by import/collection error"
PASSES = "passes without the fix"
NOT_VERIFIABLE = "not verifiable"

VERIFY_RED = Path(__file__).resolve().parent / "verify-red.sh"
# A name the fix adds is missing: an import of it, or an attribute lookup on a
# MODULE (monkeypatch.setattr in a fixture or the body). An AttributeError on
# an ordinary object is behaviour, and stays a real red.
_IMPORT_ERROR = re.compile(
    r"\b(ImportError|ModuleNotFoundError)\b"
    r"|AttributeError: (module '[^']+'|<module [^>]+>) has no attribute"
)

Outcome = tuple[str, str]  # (passed|failed|error|skipped, message)


class InfraError(Exception):
    """The check could not run; says nothing about the pull request."""


# ---------------------------------------------------------------------------
# Decisions (no I/O)
# ---------------------------------------------------------------------------


def _is_test_file(p: PurePosixPath) -> bool:
    if p.suffix != ".py" or not p.name.startswith("test_"):
        return False
    parts = p.parts
    return parts[0] == "tests" or (
        len(parts) > 3 and parts[0] == "extensions" and parts[2] == "tests"
    )


def _is_impl_file(p: PurePosixPath) -> bool:
    if p.suffix != ".py":
        return False
    parts = p.parts
    return parts[0] == "pyrite" or (
        len(parts) > 3 and parts[0] == "extensions" and parts[2] == "src"
    )


def split_changed(files: list[str]) -> tuple[list[str], list[str]]:
    """(test files, implementation files), each sorted; everything else is dropped."""
    tests, impl = [], []
    for f in files:
        p = PurePosixPath(f)
        if _is_test_file(p):
            tests.append(f)
        elif _is_impl_file(p):
            impl.append(f)
    return sorted(tests), sorted(impl)


def _test_defs(src: str | None) -> dict[tuple[str, ...], str]:
    """Test functions by (class..., name) -> an AST dump (no line numbers or comments)."""
    if src is None:
        return {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    out: dict[tuple[str, ...], str] = {}

    def walk(body: list[ast.stmt], prefix: tuple[str, ...]) -> None:
        for node in body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
                "test"
            ):
                out[prefix + (node.name,)] = ast.dump(node)
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                walk(node.body, prefix + (node.name,))

    walk(tree.body, ())
    return out


def touched_tests(base_src: str | None, head_src: str) -> set[tuple[str, ...]]:
    """The tests the PR added or edited: absent at the base, or a different AST."""
    base, head = _test_defs(base_src), _test_defs(head_src)
    return {key for key, dump in head.items() if base.get(key) != dump}


def classify(head: Outcome, reverted: Outcome | None, *, collection_error: bool) -> tuple[str, str]:
    """(label, detail) for one test, from its run with the fix and without it."""
    if head[0] != "passed":
        return NOT_VERIFIABLE, f"{head[0]} with the fix"
    if reverted is None:
        if collection_error:
            return RED_IMPORT, "the file does not import without the fix"
        return NOT_VERIFIABLE, "not run without the fix"
    state, message = reverted
    if state == "passed":
        return PASSES, ""
    if state == "skipped":
        return NOT_VERIFIABLE, "skipped without the fix"
    first = message.strip().splitlines()[0] if message.strip() else state
    if _IMPORT_ERROR.search(message):
        return RED_IMPORT, first
    return RED, first


# ---------------------------------------------------------------------------
# JUnit
# ---------------------------------------------------------------------------


@dataclass
class Report:
    outcomes: dict[str, Outcome]  # node id -> outcome
    keys: dict[str, tuple[str, ...]]  # node id -> (class..., function)
    collection_error: bool


def read_junit(path: Path, test_file: str) -> Report:
    if not path.exists():
        raise InfraError(f"pytest wrote no report for {test_file}")
    stem = PurePosixPath(test_file).stem
    outcomes: dict[str, Outcome] = {}
    keys: dict[str, tuple[str, ...]] = {}
    collection_error = False
    for case in ET.parse(path).getroot().iter("testcase"):
        classname, name = case.get("classname", ""), case.get("name", "")
        if not classname:
            collection_error = True
            continue
        # classname is the dotted module path plus any classes: keep what follows
        # the module's own name, whatever rootdir the dotted prefix came from.
        parts = classname.split(".")
        classes = tuple(parts[parts.index(stem) + 1 :]) if stem in parts else ()
        nodeid = "::".join((test_file, *classes, name))
        state, message = "passed", ""
        for tag in ("failure", "error", "skipped"):
            el = case.find(tag)
            if el is not None:
                state = {"failure": "failed"}.get(tag, tag)
                message = el.get("message", "") or (el.text or "")
                break
        outcomes[nodeid] = (state, message)
        keys[nodeid] = (*classes, name.split("[", 1)[0])
    return Report(outcomes, keys, collection_error)


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 120  # seconds per pytest run, so one hung file is a row, not a killed job


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise InfraError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _show(rev: str, path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def changed_since(mb: str) -> tuple[list[str], list[str]]:
    """(test files to run, implementation paths to revert) since the merge base.

    --no-renames turns a rename into delete + add, so the old path is reverted
    (restored from the merge base) and the new one removed. A deleted test file
    cannot be run; a deleted implementation file is put back for the run.
    """
    status = _git("diff", "--name-status", "--no-renames", "--diff-filter=ACMD", mb, "HEAD")
    present, every = [], []
    for line in status.splitlines():
        code, _, path = line.partition("\t")
        every.append(path)
        if code != "D":
            present.append(path)
    tests, _ = split_changed(present)
    _, impl = split_changed(every)
    return tests, impl


# PYTHONDONTWRITEBYTECODE: CPython validates a .pyc by the source's mtime (whole
# seconds) and size. A fix and its reverted source of the same size, swapped
# inside one second, would otherwise serve one run the other's bytecode -- the
# next file's with-fix run then fails on the reverted code, and a local tree is
# left importing it.
_RUN_ENV = {"PYTHONDONTWRITEBYTECODE": "1"}


def _run(cmd: list[str], env: dict[str, str], timeout: float) -> tuple[int | None, str]:
    """(exit code or None on timeout, stderr). A timeout TERMs the whole process
    group -- bash and the pytest under it -- so verify-red.sh's restore trap runs;
    KILL follows only if that does not end it."""
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        _, err = proc.communicate(timeout=timeout)
        return proc.returncode, err
    except subprocess.TimeoutExpired:
        for sig, grace in ((signal.SIGTERM, 10), (signal.SIGKILL, 10)):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                proc.communicate(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                continue
        return None, ""


def _restore(impl: list[str]) -> None:
    """Put the implementation back as committed, whatever state a killed run left."""
    for path in impl:
        if _show("HEAD", path) is not None:
            subprocess.run(["git", "checkout", "-q", "HEAD", "--", path], capture_output=True)
        else:
            subprocess.run(
                ["git", "rm", "-q", "--cached", "--ignore-unmatch", "--", path],
                capture_output=True,
            )
            Path(path).unlink(missing_ok=True)


def _junit_args(path: Path) -> list[str]:
    return [f"--junitxml={path}", "-o", "junit_family=xunit1"]


class NoVerdictError(Exception):
    """One file produced no verdict; it becomes a row, the run goes on."""


def run_with_fix(python: str, test_file: str, junit: Path, timeout: float) -> Report:
    code, _ = _run(
        [python, "-m", "pytest", test_file, "-q", "-p", "no:cacheprovider", *_junit_args(junit)],
        {**os.environ, **_RUN_ENV},
        timeout,
    )
    if code is None:
        raise NoVerdictError(f"timed out with the fix ({timeout:g} s)")
    if not junit.exists():
        raise NoVerdictError("no report with the fix")
    return read_junit(junit, test_file)


def run_without_fix(
    python: str, base: str, test_file: str, impl: list[str], junit: Path, timeout: float
) -> Report:
    env = {
        **os.environ,
        **_RUN_ENV,
        "VERIFY_RED_BASE": base,
        "VERIFY_RED_PYTHON": python,
        "VERIFY_RED_JUNITXML": str(junit),
    }
    code, err = _run(["bash", str(VERIFY_RED), test_file, *impl], env, timeout)
    if code is None:
        _restore(impl)
        raise NoVerdictError(f"timed out without the fix ({timeout:g} s)")
    if code not in (0, 1):
        # verify-red.sh refused (wrong tree, uncommitted edits): true of every file.
        raise InfraError(err.strip() or f"verify-red.sh exited {code}")
    if not junit.exists():
        # e.g. a conftest that imports a name the fix adds: pytest stops before any test.
        raise NoVerdictError("no report without the fix (pytest stopped before running a test)")
    return read_junit(junit, test_file)


@dataclass
class Row:
    nodeid: str
    test_file: str
    label: str
    detail: str
    touched: bool


def verify_file(
    test_file: str,
    i: int,
    *,
    mb: str,
    base: str,
    impl: list[str],
    python: str,
    tmp: Path,
    timeout: float,
) -> list[Row]:
    touched = touched_tests(_show(mb, test_file), Path(test_file).read_text())
    try:
        head = run_with_fix(python, test_file, tmp / f"head-{i}.xml", timeout)
        if head.collection_error and not head.outcomes:
            raise NoVerdictError("does not collect with the fix")
        reverted = run_without_fix(python, base, test_file, impl, tmp / f"base-{i}.xml", timeout)
    except NoVerdictError as exc:
        return [Row(test_file, test_file, NOT_VERIFIABLE, str(exc), True)]
    rows = []
    for nodeid, outcome in head.outcomes.items():
        label, detail = classify(
            outcome, reverted.outcomes.get(nodeid), collection_error=reverted.collection_error
        )
        rows.append(Row(nodeid, test_file, label, detail, head.keys[nodeid] in touched))
    return rows


# ---------------------------------------------------------------------------
# Output -- written file by file, so a job killed part-way keeps what it found
# ---------------------------------------------------------------------------


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")[:160]


def _table(rows: list[Row]) -> list[str]:
    lines = ["| Test | Without the fix | Detail |", "|---|---|---|"]
    lines += [f"| `{r.nodeid}` | {r.label} | {_cell(r.detail)} |" for r in rows]
    return lines


TITLE = "## verify-red: do this PR's tests fail without its fix?"
LEGEND = (
    f"*{RED}*: the evidence a review asks for. *{RED_IMPORT}*: weak -- the test needs "
    f"the new code (a name it imports or patches), not necessarily what it does. *{PASSES}*: "
    f"the test does not exercise the change (a warning, not a failure). *{NOT_VERIFIABLE}*: "
    "skipped, failing, timed out or unreported -- no claim."
)


def render_header(impl: list[str], mb: str) -> str:
    reverted = ", ".join(f"`{f}`" for f in impl)
    return f"{TITLE}\n\nReverted to the merge base `{mb[:10]}`: {reverted}.\n\n"


def render_file(test_file: str, rows: list[Row]) -> str:
    out = [f"### `{test_file}`", ""]
    mine = [r for r in rows if r.touched]
    rest = [r for r in rows if not r.touched]
    if mine:
        out += [*_table(mine), ""]
    else:
        out += ["This PR adds or edits no test functions here.", ""]
    if rest:
        out += [
            f"<details><summary>{len(rest)} other tests in this file (not a signal)</summary>",
            "",
            *_table(rest),
            "",
            "</details>",
            "",
        ]
    return "\n".join(out) + "\n"


def render_nothing(tests: list[str], impl: list[str]) -> str:
    missing = "test files" if not tests else "implementation files (`pyrite/`, `extensions/*/src/`)"
    return f"{TITLE}\n\nverify-red: nothing to verify -- the PR changes no {missing}.\n"


def annotations(rows: list[Row]) -> list[str]:
    return [
        f"::warning file={r.test_file},title=verify-red::{r.nodeid} passes without the fix"
        " -- it may not test the change"
        for r in rows
        if r.touched and r.label == PASSES
    ]


NO_TEST_WARNING = (
    "::warning title=verify-red::this PR changes implementation files but no test file"
    " -- nothing shows the change is tested"
)


class Sink:
    """stdout plus $GITHUB_STEP_SUMMARY, appended and flushed chunk by chunk."""

    def __init__(self, summary: str | None) -> None:
        self.summary = summary

    def write(self, text: str) -> None:
        print(text, flush=True)
        if self.summary:
            with open(self.summary, "a", encoding="utf-8") as fh:
                fh.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--base", required=True, help="the integration ref or the PR's base sha")
    parser.add_argument("--python", default=os.environ.get("VERIFY_RED_PYTHON", sys.executable))
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds per pytest run"
    )
    args = parser.parse_args(argv)
    sink = Sink(args.summary)
    try:
        mb = _git("merge-base", args.base, "HEAD").strip()
        tests, impl = changed_since(mb)
        if not tests or not impl:
            sink.write(render_nothing(tests, impl))
            if impl and not tests:
                print(NO_TEST_WARNING, flush=True)
            return 0
        sink.write(render_header(impl, mb))
        with tempfile.TemporaryDirectory(prefix="verify-red-") as tmp:
            for i, test_file in enumerate(tests):
                rows = verify_file(
                    test_file,
                    i,
                    mb=mb,
                    base=args.base,
                    impl=impl,
                    python=args.python,
                    tmp=Path(tmp),
                    timeout=args.timeout,
                )
                sink.write(render_file(test_file, rows))
                for line in annotations(rows):
                    print(line, flush=True)
        dirty = _git("status", "--porcelain", "--", *impl).strip()
        if dirty:
            raise InfraError(f"the implementation files were not restored:\n{dirty}")
        sink.write(LEGEND + "\n")
    except InfraError as exc:
        print(f"verify-red: could not run: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
