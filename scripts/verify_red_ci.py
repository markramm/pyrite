#!/usr/bin/env python3
"""verify-red: do a pull request's new tests notice its change?

    python scripts/verify_red_ci.py [--base origin/dev] [--json out.json]

It never modifies the tree it is started in. It checks the merge base out into
a throwaway ``git worktree`` under $TMPDIR, copies in the PR's test-side files
from the working tree (committed or not) and runs the tests the PR adds or
edits: the run *without the fix*. It then copies in the rest of the change, so
the throwaway tree equals the working tree, and runs them again *with the
fix*. The throwaway tree is removed. Nothing is restored, because nothing the
developer owns was changed; a run killed outright leaves a stale directory in
$TMPDIR, and once that is gone the next run prunes its registration.

Verdicts, for each new or edited test:

- **red**: passes with the fix, fails without it -- the evidence a review wants.
- **import-only**: fails without the fix only because the code it needs is
  absent: its file does not collect, or it raises ImportError, AttributeError
  or NameError naming an identifier the PR adds (an AST diff). Weak.
- **unexpected pass**: passes without the fix; it does not test the change.
  ``@pytest.mark.control`` declares a deliberate negative control instead.
- **n/a**: no claim (did not pass with the fix, skipped, not run, timed out).

Test-side files are those under ``tests/`` or ``extensions/*/tests/``, and any
``conftest.py``; everything else the PR changes is the fix. Tests the PR did not
add or edit (compared by AST, so formatting does not count) are a count.

Exit 0 whatever the verdicts; 2 when the check itself could not run.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

RED, IMPORT_ONLY, UNEXPECTED, NA, CONTROL = (
    "red",
    "import-only",
    "unexpected pass",
    "n/a",
    "control",
)
VERDICTS = (RED, IMPORT_ONLY, UNEXPECTED, NA, CONTROL)
PLUGIN = Path(__file__).resolve().parent / "verify_red_record.py"
_MISSING_NAME = {"ImportError", "AttributeError", "NameError"}
_QUOTED = re.compile(r"'([A-Za-z_][\w.]*)'")
_IDENT = re.compile(r"[A-Za-z_]\w*\Z")


class InfraError(Exception):
    """The check could not run; says nothing about the pull request."""


# ---------------------------------------------------------------------------
# Decisions (no I/O)
# ---------------------------------------------------------------------------


def is_test_side(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (
        parts[0] == "tests"
        or (len(parts) > 3 and parts[0] == "extensions" and parts[2] == "tests")
        or parts[-1] == "conftest.py"
    )


def is_test_file(path: str) -> bool:
    p = PurePosixPath(path)
    return is_test_side(path) and p.suffix == ".py" and p.name.startswith("test_")


def _parse(src: str | None) -> ast.Module | None:
    try:
        return ast.parse(src) if src is not None else None
    except SyntaxError:
        return None


def _test_defs(src: str | None) -> dict[tuple[str, ...], str]:
    """Test functions by (class..., name) -> an AST dump (no line numbers or comments)."""
    out: dict[tuple[str, ...], str] = {}

    def walk(body: list[ast.stmt], prefix: tuple[str, ...]) -> None:
        for node in body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name.startswith("test"):
                    out[prefix + (node.name,)] = ast.dump(node)
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                walk(node.body, prefix + (node.name,))

    tree = _parse(src)
    walk(tree.body if tree else [], ())
    return out


def touched_tests(base_src: str | None, head_src: str) -> set[tuple[str, ...]]:
    """The tests the PR added or edited: absent at the base, or a different AST."""
    base, head = _test_defs(base_src), _test_defs(head_src)
    return {k for k, dump in head.items() if base.get(k) != dump}


def defined_names(src: str | None) -> set[str]:
    """Every function, class, and module- or class-level variable a source defines."""
    tree = _parse(src)
    if tree is None:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        if isinstance(node, ast.Module | ast.ClassDef):
            for stmt in node.body:
                targets = stmt.targets if isinstance(stmt, ast.Assign) else []
                targets = [stmt.target] if isinstance(stmt, ast.AnnAssign) else targets
                names |= {t.id for t in targets if isinstance(t, ast.Name)}
    return names


def module_names(path: str) -> set[str]:
    """The dotted module a source file is imported as, and its last part."""
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts[0] == "extensions" and len(parts) > 3 and parts[2] == "src":
        parts = parts[3:]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return {".".join(parts), parts[-1]} if parts else set()


def _named(exc: dict) -> set[str]:
    """The identifiers an exception's own arguments name (quoted, or a bare name)."""
    found: set[str] = set()
    for arg in exc.get("args", []):
        found |= set(_QUOTED.findall(arg))
        if _IDENT.match(arg):
            found.add(arg)  # monkeypatch.delattr raises AttributeError(name)
    return found


def classify(
    with_fix: dict | None,
    without: dict | None,
    *,
    collect_failed: bool,
    control: bool,
    added: frozenset[str] | set[str],
) -> tuple[str, str]:
    """(verdict, detail) for one test, from its record in each run."""
    if with_fix is None or with_fix["outcome"] != "passed":
        return NA, f"{with_fix['outcome'] if with_fix else 'not run'} with the fix"
    if collect_failed:
        return IMPORT_ONLY, "its file does not collect without the fix"
    if without is None or without["outcome"] == "skipped":
        return NA, f"{without['outcome'] if without else 'not run'} without the fix"
    if without["outcome"] == "passed":
        return (CONTROL, "") if control else (UNEXPECTED, "")
    exc = without.get("exc") or {}
    missing = _named(exc) & added if _MISSING_NAME & set(exc.get("types", [])) else set()
    if missing:
        return IMPORT_ONLY, f"{', '.join(sorted(missing))}: added by the PR"
    return RED, ""


def summary_line(counts: dict[str, int]) -> str:
    line = " · ".join(f"{counts[v]} {v}" for v in (RED, IMPORT_ONLY, UNEXPECTED, NA))
    return f"verify-red: {line}" + (f" · {counts[CONTROL]} control" if counts[CONTROL] else "")


def _key(nodeid: str) -> tuple[str, ...]:
    return tuple(nodeid.split("[", 1)[0].split("::"))  # a parameter id may hold "::"


# ---------------------------------------------------------------------------
# Reading the developer's repository (read-only)
# ---------------------------------------------------------------------------


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise InfraError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _show(top: Path, rev: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=top, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


@dataclass
class Change:
    test_side: list[str]  # copied in for both runs
    code: list[str]  # copied in for the run with the fix
    selected: list[tuple[str, ...]]  # (file, class..., function) of each new or edited test
    pre_existing: int
    added: frozenset[str]  # identifiers the code change defines


def read_change(top: Path, mb: str) -> Change:
    tracked = git("diff", "--name-only", "--no-renames", "-z", mb, cwd=top).split("\0")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z", cwd=top).split("\0")
    paths = sorted({p for p in tracked + untracked if p})
    status = git("diff", "-M", "--diff-filter=R", "--name-status", "-z", mb, cwd=top).split("\0")
    renamed_from = {status[i + 2]: status[i + 1] for i in range(0, len(status) - 2, 3)}
    test_side = [p for p in paths if is_test_side(p)]
    code = [p for p in paths if not is_test_side(p)]
    added: set[str] = set()
    for p in (p for p in code if p.endswith(".py") and (top / p).is_file()):
        before = _show(top, mb, p)
        added |= defined_names((top / p).read_text(errors="replace")) - defined_names(before)
        added |= module_names(p) if before is None else set()
    selected, pre_existing = [], 0
    for f in (p for p in test_side if is_test_file(p) and (top / p).is_file()):
        head = (top / f).read_text(errors="replace")
        touched = touched_tests(_show(top, mb, renamed_from.get(f, f)), head)
        selected += [(f, *k) for k in sorted(touched)]
        pre_existing += len(_test_defs(head)) - len(touched)
    return Change(test_side, code, selected, pre_existing, frozenset(added))


# ---------------------------------------------------------------------------
# The throwaway tree
# ---------------------------------------------------------------------------


def overlay(src: Path, dst: Path, paths: list[str]) -> None:
    """Make each path in `dst` what it is in `src`: a copy, or absent."""
    for p in paths:
        s, d = src / p, dst / p
        if d.is_symlink() or d.is_file():
            d.unlink()
        if s.is_symlink() or s.is_file():
            d.parent.mkdir(parents=True, exist_ok=True)
            d.symlink_to(os.readlink(s)) if s.is_symlink() else shutil.copy2(s, d)


def import_roots(tree: Path) -> list[Path]:
    return [tree, *sorted(tree.glob("extensions/*/src"))]


def check_imports(python: str, tree: Path, env: dict[str, str]) -> None:
    """#189: every package in the tree must import from the tree, not an install elsewhere."""
    pkgs = sorted({p.parent.name for r in import_roots(tree) for p in r.glob("*/__init__.py")})
    code = (
        "import importlib.util as u, json, sys\n"
        "print(json.dumps({n: getattr(u.find_spec(n), 'origin', None) for n in sys.argv[1:]}))"
    )
    r = subprocess.run(
        [python, "-c", code, *pkgs], cwd=tree, env=env, capture_output=True, text=True
    )
    if r.returncode != 0:
        raise InfraError(f"could not locate the packages under test: {r.stderr.strip()}")
    for name, origin in json.loads(r.stdout).items():
        if not origin or not Path(origin).resolve().is_relative_to(tree.resolve()):
            raise InfraError(
                f"{name} resolves outside the tree under test ({origin}): a verdict about "
                "code the interpreter is not importing is not evidence"
            )


@dataclass
class Run:
    results: dict[str, dict]  # nodeid -> the record that decides its outcome
    collect_failed: set[str]  # test files that did not collect
    timed_out: bool


def run_pytest(python: str, tree: Path, work: Path, name: str, timeout: float) -> Run:
    record = work / f"{name}.jsonl"
    env = {
        **os.environ,
        # Both runs import one tree whose sources change in between; a .pyc the
        # first wrote (same size, same mtime second) would serve it to the second.
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            [*map(str, import_roots(tree)), str(work / "plugin"), os.environ.get("PYTHONPATH", "")]
        ),
        "VERIFY_RED_RECORD": str(record),
        "VERIFY_RED_SELECT": str(work / "select.json"),
    }
    check_imports(python, tree, env)
    files = sorted({k[0] for k in json.loads((work / "select.json").read_text())})
    cmd = [python, "-m", "pytest", *files, "-p", "verify_red_record", "-p", "no:cacheprovider"]
    log = work / f"{name}.log"
    try:
        with open(log, "w") as out:
            subprocess.run(
                [*cmd, "--continue-on-collection-errors"],
                cwd=tree,
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
    phases: dict[str, list[dict]] = {}
    collect_failed = set()
    for rec in map(json.loads, record.read_text().splitlines() if record.exists() else []):
        if "collect" in rec:
            collect_failed.add(rec["collect"])
        else:
            phases.setdefault(rec["nodeid"], []).append(rec)
    if not phases and not timed_out:
        tail = log.read_text().splitlines()[-15:]
        print(f"verify-red: the {name} run recorded no test:", *tail, sep="\n  ", file=sys.stderr)
    results = {}
    for nodeid, recs in phases.items():
        # A failed or skipped phase decides; otherwise it passed only once its
        # call phase finished (a run killed mid-test has recorded setup alone).
        final = next((r for r in recs if r["outcome"] == "failed"), None)
        final = final or next((r for r in recs if r["outcome"] == "skipped"), None)
        final = final or next((r for r in recs if r["when"] == "call"), None)
        if final:
            results[nodeid] = final
    return Run(results, collect_failed, timed_out)


def verify(python: str, top: Path, mb: str, change: Change, timeout: float) -> tuple[Run, Run]:
    """(run without the fix, run with it), in one throwaway tree."""
    git("worktree", "prune", cwd=top)  # a killed run's tree, once $TMPDIR has lost it
    work = Path(tempfile.mkdtemp(prefix="verify-red-"))
    tree = work / "tree"
    try:
        git("worktree", "add", "--detach", "-q", str(tree), mb, cwd=top)
        (work / "plugin").mkdir()
        shutil.copy(PLUGIN, work / "plugin")
        (work / "select.json").write_text(json.dumps(change.selected))
        overlay(top, tree, change.test_side)
        without = run_pytest(python, tree, work, "without", timeout)
        overlay(top, tree, change.code)
        return without, run_pytest(python, tree, work, "with", timeout)
    finally:
        remove = ["git", "worktree", "remove", "--force", str(tree)]
        subprocess.run(remove, cwd=top, capture_output=True)
        shutil.rmtree(work, ignore_errors=True)


def verdicts(change: Change, without: Run, with_fix: Run) -> list[tuple[str, str, str]]:
    """(nodeid, verdict, detail) for every selected test, parameters expanded."""
    rows = []
    for nodeid in sorted(set(with_fix.results) | set(without.results)):
        w, wo = with_fix.results.get(nodeid), without.results.get(nodeid)
        verdict, detail = classify(
            w,
            wo,
            collect_failed=nodeid.split("::")[0] in without.collect_failed,
            control=bool((w or wo or {}).get("control")),
            added=change.added,
        )
        if verdict == NA and (w is None and with_fix.timed_out or wo is None and without.timed_out):
            detail = "not reached: the run timed out"
        rows.append((nodeid, verdict, detail))
    seen = {_key(n) for n, _, _ in rows}
    for k in (k for k in change.selected if k not in seen):
        if k[0] in with_fix.collect_failed:
            detail = "its file does not collect with the fix"
        elif with_fix.timed_out or without.timed_out:
            detail = "not reached: the run timed out"
        else:
            detail = "not collected"
        rows.append(("::".join(k), NA, detail))
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

LEGEND = (
    "*red* (not listed): fails without the fix -- the evidence a review wants. *import-only*: "
    "fails only because a name the PR adds is missing -- weak. *unexpected pass*: passes "
    "without the fix, so it does not test the change (`@pytest.mark.control` marks a "
    "deliberate negative control). *n/a*: no claim."
)


def _default_base(top: Path) -> str:
    probe = ["git", "rev-parse", "-q", "--verify", "origin/dev"]
    return (
        "origin/dev"
        if subprocess.run(probe, cwd=top, capture_output=True).returncode == 0
        else "dev"
    )


def report(args: argparse.Namespace) -> tuple[dict, str]:
    """(the evidence, the markdown for stdout and the step summary)."""
    top = Path(git("rev-parse", "--show-toplevel", cwd=Path.cwd()).strip())
    mb = git("merge-base", args.base or _default_base(top), "HEAD", cwd=top).strip()
    change = read_change(top, mb)
    subjects = git("log", "--format=%s", f"{mb}..HEAD", cwd=top).splitlines()
    evidence: dict = {
        "pr": args.pr,
        "head": git("rev-parse", "HEAD", cwd=top).strip(),
        "merge_base": mb,
        "fix_commits": sum(bool(re.match(r"fix(\(.*\))?!?:", s)) for s in subjects),
        "verify_red": None,
        "diff_coverage": None,
    }
    out = ["## verify-red: do this PR's new tests fail without its change?", ""]
    ci = os.environ.get("GITHUB_ACTIONS") == "true"
    if not change.code or not change.selected:
        why = "no code change" if not change.code else "no new or edited test"
        out.append(f"verify-red: nothing to verify ({why}).")
        if change.code and ci:
            print(f"::warning title=verify-red::this PR changes code but has {why}", flush=True)
    else:
        rows = verdicts(change, *verify(args.python, top, mb, change, args.timeout))
        counts = {v: sum(r[1] == v for r in rows) for v in VERDICTS}
        n = change.pre_existing
        tail = f"({n} pre-existing test{'s' * (n != 1)} in these files not run)"
        out += [f"{summary_line(counts)} {tail}", ""]
        listed = [r for r in rows if r[1] != RED]
        if listed:
            out += ["| Test | Verdict | Detail |", "|---|---|---|"]
            out += [f"| `{t}` | {v} | {d.replace('|', '/')[:160]} |" for t, v, d in listed]
            out.append("")
        out.append(LEGEND)
        for t, v, _ in listed:
            if ci and v == UNEXPECTED:
                print(
                    f"::warning file={t.split('::')[0]},title=verify-red::{t} passes without the fix"
                )
        evidence["verify_red"] = {**counts, "pre-existing": n}
    if args.diff_cover_json and Path(args.diff_cover_json).is_file():
        dc = json.loads(Path(args.diff_cover_json).read_text())
        d = evidence["diff_coverage"] = {
            "percent": dc.get("total_percent_covered"),
            "lines": dc.get("total_num_lines"),
            "uncovered": dc.get("total_num_violations"),
        }
        out += ["", f"diff coverage: {d['percent']}% of {d['lines']} changed lines (advisory)"]
    return evidence, "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--base", help="the integration ref (default origin/dev, else dev)")
    parser.add_argument("--python", default=os.environ.get("VERIFY_RED_PYTHON", sys.executable))
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    parser.add_argument("--timeout", type=float, default=600, help="seconds per pytest run")
    parser.add_argument("--json", help="write the evidence (verdict counts, diff coverage) here")
    parser.add_argument("--diff-cover-json", help="diff-cover's JSON report, carried into --json")
    parser.add_argument("--pr", type=int, help="the pull request number, for --json")
    args = parser.parse_args(argv)
    try:
        evidence, text = report(args)
    except InfraError as exc:
        print(f"verify-red: could not run: {exc}", file=sys.stderr)
        return 2
    print(text, flush=True)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if args.json:
        Path(args.json).write_text(json.dumps(evidence, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
