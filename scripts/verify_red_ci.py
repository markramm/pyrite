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
- **not verifiable** -- it did not pass with the fix (skipped, failed), or was
  skipped without it. No claim either way.

Tests the PR did not add or edit (compared by AST, so formatting does not
count) are listed separately and never warned about.

The table goes to ``$GITHUB_STEP_SUMMARY`` (and stdout). Exit 0 whatever the
verdicts; exit 2 only when the check itself could not run -- verify-red.sh
refused, a report is missing, git failed. It is a signal, not a gate.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
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
_IMPORT_ERROR = re.compile(r"\b(ImportError|ModuleNotFoundError)\b")

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


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise InfraError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _show(rev: str, path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def _junit_args(path: Path) -> list[str]:
    return [f"--junitxml={path}", "-o", "junit_family=xunit1"]


def run_with_fix(python: str, test_file: str, junit: Path) -> Report:
    subprocess.run(
        [python, "-m", "pytest", test_file, "-q", "-p", "no:cacheprovider", *_junit_args(junit)],
        capture_output=True,
        text=True,
    )
    return read_junit(junit, test_file)


def run_without_fix(python: str, base: str, test_file: str, impl: list[str], junit: Path) -> Report:
    env = {
        **os.environ,
        "VERIFY_RED_BASE": base,
        "VERIFY_RED_PYTHON": python,
        "VERIFY_RED_JUNITXML": str(junit),
    }
    result = subprocess.run(
        ["bash", str(VERIFY_RED), test_file, *impl], env=env, capture_output=True, text=True
    )
    if result.returncode not in (0, 1):
        raise InfraError(result.stderr.strip() or f"verify-red.sh exited {result.returncode}")
    return read_junit(junit, test_file)


@dataclass
class Row:
    nodeid: str
    test_file: str
    label: str
    detail: str
    touched: bool


def verify(base: str, python: str) -> tuple[list[Row], list[str], list[str], str]:
    mb = _git("merge-base", base, "HEAD").strip()
    changed = _git("diff", "--name-only", "--diff-filter=ACMR", mb, "HEAD").split()
    tests, impl = split_changed(changed)
    rows: list[Row] = []
    if not tests or not impl:
        return rows, tests, impl, mb
    with tempfile.TemporaryDirectory(prefix="verify-red-") as tmp:
        for i, test_file in enumerate(tests):
            touched = touched_tests(_show(mb, test_file), Path(test_file).read_text())
            head = run_with_fix(python, test_file, Path(tmp) / f"head-{i}.xml")
            reverted = run_without_fix(python, base, test_file, impl, Path(tmp) / f"base-{i}.xml")
            if head.collection_error and not head.outcomes:
                rows.append(
                    Row(test_file, test_file, NOT_VERIFIABLE, "does not collect with the fix", True)
                )
            for nodeid, outcome in head.outcomes.items():
                label, detail = classify(
                    outcome,
                    reverted.outcomes.get(nodeid),
                    collection_error=reverted.collection_error,
                )
                rows.append(Row(nodeid, test_file, label, detail, head.keys[nodeid] in touched))
    dirty = _git("status", "--porcelain", "--", *impl).strip()
    if dirty:
        raise InfraError(f"the implementation files were not restored:\n{dirty}")
    return rows, tests, impl, mb


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")[:160]


def _table(rows: list[Row]) -> list[str]:
    lines = ["| Test | Without the fix | Detail |", "|---|---|---|"]
    lines += [f"| `{r.nodeid}` | {r.label} | {_cell(r.detail)} |" for r in rows]
    return lines


def render(rows: list[Row], tests: list[str], impl: list[str], mb: str) -> str:
    out = ["## verify-red: do this PR's tests fail without its fix?", ""]
    if not tests or not impl:
        missing = (
            "test files" if not tests else "implementation files (`pyrite/`, `extensions/*/src/`)"
        )
        out.append(f"verify-red: nothing to verify -- the PR changes no {missing}.")
        return "\n".join(out) + "\n"
    reverted = ", ".join(f"`{f}`" for f in impl)
    out += [f"Reverted to the merge base `{mb[:10]}`: {reverted}.", ""]
    mine = [r for r in rows if r.touched]
    rest = [r for r in rows if not r.touched]
    if mine:
        out += ["Tests this PR adds or edits:", "", *_table(mine), ""]
    else:
        out += ["This PR adds or edits no test functions in the changed test files.", ""]
    if rest:
        out += [
            f"<details><summary>{len(rest)} other tests in the same files (not a signal)</summary>",
            "",
            *_table(rest),
            "",
            "</details>",
            "",
        ]
    out += [
        f"*{RED}*: the evidence a review asks for. *{RED_IMPORT}*: weak -- the test needs "
        f"the new code, not necessarily what it does. *{PASSES}*: the test does not exercise "
        f"the change (a warning, not a failure). *{NOT_VERIFIABLE}*: skipped or failing, no claim.",
    ]
    return "\n".join(out) + "\n"


def annotations(rows: list[Row]) -> list[str]:
    return [
        f"::warning file={r.test_file},title=verify-red::{r.nodeid} passes without the fix"
        " -- it may not test the change"
        for r in rows
        if r.touched and r.label == PASSES
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--base", required=True, help="the integration ref or the PR's base sha")
    parser.add_argument("--python", default=os.environ.get("VERIFY_RED_PYTHON", sys.executable))
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    args = parser.parse_args(argv)
    try:
        rows, tests, impl, mb = verify(args.base, args.python)
    except InfraError as exc:
        print(f"verify-red: could not run: {exc}", file=sys.stderr)
        return 2
    text = render(rows, tests, impl, mb)
    print(text)
    for line in annotations(rows):
        print(line)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
