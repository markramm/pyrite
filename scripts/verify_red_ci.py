#!/usr/bin/env python3
"""Do a pull request's tests fail without its fix? The one owner of that check.

    python scripts/verify_red_ci.py --base <base ref or sha>          # the CI job (#352)
    python scripts/verify_red_ci.py --test <node id> <impl file>...   # scripts/verify-red.sh

This script alone reverts implementation files to the merge base and puts them
back (retro 10, #368): ``scripts/verify-red.sh`` is a wrapper that calls it with
``--test``. Before #374 the shell script reverted and restored with ``git
checkout`` in an EXIT trap and this driver ran a second, content-based restore
behind it; every disagreement between the two was a data-loss or wrong-verdict
path.

**The revert** (``plan`` + ``reverted``). Each named file must be exactly as
committed -- its bytes, run through the path's clean filter (``git hash-object
--path``), are HEAD's blob, and its index entry is HEAD's -- or nothing runs.
Its bytes are kept in memory, and the merge base's content is written in place
as a checkout would write it (``git cat-file --filters``, so ``eol=crlf`` and
smudge filters hold); a file absent at the merge base is removed. The index is
never written: no ``git checkout``, ``git rm`` or ``git status``, so an
interrupt cannot strand ``.git/index.lock`` or leave a staged merge-base file.

**The restore**, in one ``finally``, file by file: a file that still holds what
the revert wrote gets its original bytes back (mode kept); a file already back
at its original needs nothing; anything else was edited during the run and is
left as the editor left it. SIGINT, SIGTERM, SIGHUP and SIGQUIT wait until the
restore ends.
Every file is attempted; the ones that could not be restored are named on
stderr and the exit is non-zero (2, or the signal's own status).

**Classification** (``--base``): the changes since the merge base with
``--base`` split into test files (``tests/**/test_*.py``,
``extensions/*/tests/**/test_*.py``) and implementation (``.py`` under
``pyrite/`` and ``extensions/*/src/``). Each changed test file runs twice, with
the fix and with every implementation file reverted, and each test is:

- **red without the fix** -- it failed on an assertion or error of its own:
  the evidence the review lane asks for.
- **red by import/collection error** -- it failed because a name the fix adds
  does not exist yet (an import, a module lookup, a ``monkeypatch`` or
  ``unittest.mock`` patch of it). Weak: it proves the test needs the new code,
  not that it checks what the code does.
- **passes without the fix** -- it does not test the change. A warning
  annotation on the PR, for a test the PR adds or edits; never a failure.
- **not verifiable** -- it did not pass with the fix (skipped, failed), was
  skipped without it, or its file timed out (``--timeout``, 120 s per run) or
  produced no report (a conftest importing a name the fix adds). No claim
  either way; the other files still run.

Implementation paths include the old side of a rename and deleted files, so
the reverted run sees the merge base's layout and the restore puts the PR's
back. Every run sets PYTHONDONTWRITEBYTECODE and the revert drops each file's
cached bytecode (see ``_RUN_ENV``); before anything is reverted, each package
must import from this tree (#189).

Tests the PR did not add or edit (compared by AST, so formatting does not
count) are listed separately and never warned about.

The table goes to ``$GITHUB_STEP_SUMMARY`` (and stdout) one file at a time, so
a job killed part-way keeps what it found. A PR that changes implementation but
no test file gets a warning. Exit 0 whatever the verdicts; exit 2 only when the
check itself could not run -- a refusal, git failed, the tree was not restored.
It is a signal, not a gate.

``--test`` exits 0 when the test fails without the fix, 1 when it passes
anyway, 2 when no claim can be made.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

RED = "red without the fix"
RED_IMPORT = "red by import/collection error"
PASSES = "passes without the fix"
NOT_VERIFIABLE = "not verifiable"

# A name the fix adds is missing: an import of it, a lookup on a module, or a
# patch of it (in a fixture or the body). The forms, as the exception line of
# the JUnit message carries them:
#   ImportError / ModuleNotFoundError: ...              an import
#   module 'pkg.mod' has no attribute 'x'              Python, module lookup
#   <module 'pkg.mod' from '...'> has no attribute 'x' monkeypatch.setattr, module object
#   'module' object at pkg.mod has no attribute 'x'    monkeypatch, "pkg.mod.x" string
#   <class 'pkg.mod.C'> has no attribute 'x'           monkeypatch.setattr, class target
#   <module ...> / <class ...> does not have the attribute 'x'
#                                                      unittest.mock.patch / patch.object
#   AttributeError: x                                  monkeypatch.delattr (the bare name)
# Python's own class lookup ("type object 'C' has no attribute") and any lookup
# or patch on an instance are behaviour, and stay a real red. Only the exception
# line is read: "AssertionError: assert 'ImportError: x' == ..." is an assertion.
_WEAK_RED = re.compile(
    r"(?:ImportError|ModuleNotFoundError): "
    r"|AttributeError: (?:module '[^']+'|<module [^>]+>|'module' object at \S+|<class '[^']+'>)"
    r" (?:has no attribute|does not have the attribute) "
    r"|AttributeError: [A-Za-z_]\w*$"
)
# A fixture's error: `failed on setup with "AttributeError: ..."`.
_PHASE = re.compile(r'failed on (?:setup|teardown) with "(.*)"\Z', re.DOTALL)


def exception_line(message: str) -> str:
    """The line naming the exception a JUnit failure message reports."""
    text = message.strip()
    phase = _PHASE.match(text)
    if phase:
        text = phase.group(1).strip()
    return text.splitlines()[0] if text else ""


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
    if _WEAK_RED.match(exception_line(message)):
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
KILL_GRACE = 20  # _run's TERM-then-KILL waits (10 s each) after a timeout
MIN_RUN = 5  # a run given less than this is not started


def run_timeout(timeout: float, remaining: float | None) -> float | None:
    """The timeout for the next run: the per-run timeout, cut to what the job's
    budget has left after setting the kill grace aside. None: too little left to
    start one -- the file becomes a row rather than the job being cancelled."""
    if remaining is None:
        return timeout
    left = remaining - KILL_GRACE
    return min(timeout, left) if left >= MIN_RUN else None


def _git(*args: str, stdin: bytes | None = None) -> str:
    """git's stdout, or InfraError. No command used here writes the index."""
    result = subprocess.run(["git", *args], input=stdin, capture_output=True)
    if result.returncode != 0:
        raise InfraError(f"git {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout.decode(errors="replace")


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


# ---------------------------------------------------------------------------
# The revert and the restore -- this module is their only owner
# ---------------------------------------------------------------------------


@dataclass
class Target:
    """One file the run reverts: what was on disk, and what the revert writes."""

    path: str
    original: bytes | None  # the committed file as it was on disk; None: absent at HEAD
    mode: int  # its permission bits, kept across the revert and the restore
    base: bytes | None  # the merge base's content as a checkout writes it; None: absent there


def _blob_id(rev: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"{rev}:{path}"], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _read(path: str) -> bytes | None:
    """The file's bytes; None if it does not exist. Any other OSError propagates."""
    try:
        return Path(path).read_bytes()
    except FileNotFoundError:
        return None


def _committed(path: str, disk: bytes | None, head: str | None) -> bool:
    """Whether `disk` is the file HEAD has: the blob `git add` would make of these
    bytes (clean filter and eol conversion for this path) is HEAD's."""
    if disk is None or head is None:
        return disk is None and head is None
    return _git("hash-object", f"--path={path}", "--stdin", stdin=disk).strip() == head


def plan(paths: list[str], mb: str) -> list[Target]:
    """The files the run will revert, each checked to be exactly as committed.

    Refuses (InfraError) on any uncommitted state -- in the file or only in the
    index -- before anything is touched. Files identical at the merge base are
    left out: there is nothing to revert.
    """
    staged = subprocess.run(["git", "diff", "--cached", "--quiet", "HEAD", "--", *paths])
    if staged.returncode != 0:
        raise InfraError(
            f"{', '.join(paths)} have uncommitted changes (in the index); commit them first"
        )
    targets = []
    for path in paths:
        head, base = _blob_id("HEAD", path), _blob_id(mb, path)
        try:
            disk = _read(path)
            mode = Path(path).stat().st_mode & 0o7777 if disk is not None else 0o644
        except OSError as exc:
            raise InfraError(f"{path}: {exc.strerror or exc}") from exc
        if not _committed(path, disk, head):
            raise InfraError(f"{path} has uncommitted changes; commit them first")
        if base == head:
            continue
        content = None
        if base is not None:
            result = subprocess.run(
                ["git", "cat-file", "--filters", f"{mb}:{path}"], capture_output=True
            )
            if result.returncode != 0:
                raise InfraError(
                    f"git cat-file --filters {mb}:{path}: {result.stderr.decode().strip()}"
                )
            content = result.stdout
        targets.append(Target(path, disk, mode, content))
    return targets


def _drop_pyc(path: str) -> None:
    """Remove the file's cached bytecode. A .pyc Python does not check against its
    source, or a timestamp one whose same-second, same-size source was swapped
    under it, would serve one version's code to a run of the other."""
    try:
        cached = Path(importlib.util.cache_from_source(path))
    except ValueError:
        return
    for pyc in cached.parent.glob(f"{Path(path).stem}.*.pyc"):
        pyc.unlink(missing_ok=True)


def _put(path: str, content: bytes | None, mode: int) -> None:
    """Make the file hold `content` (None: remove it), atomically: a temporary
    file beside it, then a rename, so no reader sees half a file."""
    target = Path(path)
    if content is None:
        target.unlink(missing_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".verify-red", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


@contextmanager
def _signals_held() -> Iterator[None]:
    """SIGINT and the ending signals wait until the block ends, then arrive as usual."""
    held = {signal.SIGINT, *ENDING_SIGNALS}
    old = signal.pthread_sigmask(signal.SIG_BLOCK, held)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


class RestoreError(InfraError):
    """Some reverted files could not be put back; each was named on stderr."""


def _restore(targets: list[Target], written: dict[str, bytes | None]) -> list[str]:
    """Put back every file the revert wrote; returns the ones that could not be,
    each with its reason. Every file is attempted. Idempotent: run again, it
    skips what is back and finds the same failures."""
    failures = []
    with _signals_held():
        for t in targets:
            if t.path not in written:
                continue
            try:
                now = _read(t.path)
                if now == t.original:
                    continue  # already back as committed
                if now != written[t.path]:
                    failures.append(
                        f"{t.path}: changed during the run, so left as it is"
                        f" (the committed version: git checkout HEAD -- {t.path})"
                    )
                    continue
                _put(t.path, t.original, t.mode)
            except OSError as exc:
                failures.append(f"{t.path}: not restored: {exc.strerror or exc}")
    return failures


@contextmanager
def reverted(targets: list[Target]) -> Iterator[None]:
    """The files hold their merge-base content inside the block; after it, however
    it ends, they hold what they held before (see ``_restore``). A restore that
    fails raises RestoreError -- unless a signal is ending the run, which
    keeps its own exit status."""
    written: dict[str, bytes | None] = {}
    ending: BaseException | None = None
    try:
        for t in targets:
            try:
                if _read(t.path) != t.original:
                    raise InfraError(f"{t.path} has uncommitted changes; commit them first")
                # Recorded before the write: an interrupt between the two leaves a
                # file still at its original, which the restore then skips.
                written[t.path] = t.base
                _put(t.path, t.base, t.mode)
                _drop_pyc(t.path)
            except OSError as exc:
                raise InfraError(f"{t.path}: not reverted: {exc.strerror or exc}") from exc
        yield
    except BaseException as exc:
        ending = exc
        raise
    finally:
        # Inline, and the first thing here: a signal whose Python handler is
        # already pending (a second Ctrl-C) raises at the next bytecode check --
        # before the mask in _signals_held is up, or as it comes down. Any such
        # raise lands inside this `try`, and the restore simply runs again.
        signalled: BaseException | None = None
        while True:
            try:
                failures = _restore(targets, written)
                break
            except (KeyboardInterrupt, SystemExit) as exc:
                signalled = signalled or exc
        for failure in failures:
            print(f"verify-red: {failure}", file=sys.stderr, flush=True)
        if signalled is not None:
            raise signalled  # the signal ends the run, with its own status
        if failures and isinstance(ending, Exception | None):
            raise RestoreError(f"{len(failures)} file(s) not restored; see above") from ending


def check_imports_here(python: str, paths: list[str]) -> None:
    """Refuse unless each reverted file's package imports from this tree (#189).

    A review worktree whose .venv is a symlink to another checkout's resolves
    packages to an editable install pointing THERE: the run then tests the wrong
    code. pyrite/... -> pyrite; extensions/<name>/src/<pkg>/... -> <pkg>.
    """
    root = Path(_git("rev-parse", "--show-toplevel").strip()).resolve()
    seen: set[str] = set()
    for path in paths:
        parts = PurePosixPath(path).parts
        if parts[0] == "pyrite":
            pkg = "pyrite"
        elif len(parts) > 4 and parts[0] == "extensions" and parts[2] == "src":
            pkg = parts[3]
        else:
            continue
        if pkg in seen:
            continue
        seen.add(pkg)
        result = subprocess.run(
            [python, "-c", f"import {pkg}, os; print(os.path.dirname({pkg}.__file__))"],
            env={**os.environ, **_RUN_ENV},
            capture_output=True,
            text=True,
        )
        resolved = result.stdout.strip()
        if result.returncode != 0 or not resolved:
            raise InfraError(
                f"`{python} -c 'import {pkg}'` failed -- cannot confirm which tree this"
                " interpreter tests"
            )
        if not Path(resolved).resolve().is_relative_to(root):
            raise InfraError(
                f"{pkg} resolves outside this worktree ({resolved}, not under {root}) -- a suite"
                " number from a tree the interpreter is not importing is not evidence"
            )


# PYTHONDONTWRITEBYTECODE: CPython validates a .pyc by the source's mtime (whole
# seconds) and size. A fix and its reverted source of the same size, swapped
# inside one second, would otherwise serve one run the other's bytecode -- the
# next file's with-fix run then fails on the reverted code, and a local tree is
# left importing it.
_RUN_ENV = {"PYTHONDONTWRITEBYTECODE": "1"}


def _run(cmd: list[str], env: dict[str, str], timeout: float | None) -> tuple[int | None, str]:
    """(exit code or None on timeout, stderr). A timeout TERMs the run's whole
    process group; KILL follows only if that does not end it."""
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
        pass
    except BaseException:
        # The driver itself is going (Ctrl-C, SIGTERM, a cancelled job). The child
        # has its own session, so nothing else would stop it: kill the group now;
        # the restore runs as the exception leaves `reverted`.
        _killpg(proc, signal.SIGKILL)
        raise
    for sig, grace in ((signal.SIGTERM, 10), (signal.SIGKILL, 10)):
        if not _killpg(proc, sig):
            break
        try:
            proc.communicate(timeout=grace)
            break
        except subprocess.TimeoutExpired:
            continue
    return None, ""


def _killpg(proc: subprocess.Popen[str], sig: int) -> bool:
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        return False
    return True


def _pytest(python: str, target: str, *extra: str) -> list[str]:
    return [python, "-m", "pytest", target, "-q", "-p", "no:cacheprovider", *extra]


def _junit_args(path: Path) -> list[str]:
    return [f"--junitxml={path}", "-o", "junit_family=xunit1"]


class NoVerdictError(Exception):
    """One file produced no verdict; it becomes a row, the run goes on."""


def run_with_fix(python: str, test_file: str, junit: Path, timeout: float) -> Report:
    code, _ = _run(
        _pytest(python, test_file, *_junit_args(junit)), {**os.environ, **_RUN_ENV}, timeout
    )
    if code is None:
        raise NoVerdictError(f"timed out with the fix ({timeout:g} s)")
    if not junit.exists():
        raise NoVerdictError("no report with the fix")
    return read_junit(junit, test_file)


def run_without_fix(
    python: str, test_file: str, targets: list[Target], junit: Path, timeout: float
) -> Report:
    with reverted(targets):
        code, _ = _run(
            _pytest(python, test_file, *_junit_args(junit)), {**os.environ, **_RUN_ENV}, timeout
        )
    if code is None:
        raise NoVerdictError(f"timed out without the fix ({timeout:g} s)")
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
    targets: list[Target],
    python: str,
    tmp: Path,
    timeout: float,
    remaining: Callable[[], float | None] = lambda: None,
) -> list[Row]:
    touched = touched_tests(_show(mb, test_file), Path(test_file).read_text())

    def budgeted() -> float:
        t = run_timeout(timeout, remaining())
        if t is None:
            raise NoVerdictError("not run: the job's time budget is spent")
        return t

    try:
        head = run_with_fix(python, test_file, tmp / f"head-{i}.xml", budgeted())
        if head.collection_error and not head.outcomes:
            raise NoVerdictError("does not collect with the fix")
        reverted_run = run_without_fix(
            python, test_file, targets, tmp / f"base-{i}.xml", budgeted()
        )
    except NoVerdictError as exc:
        return [Row(test_file, test_file, NOT_VERIFIABLE, str(exc), True)]
    rows = []
    for nodeid, outcome in head.outcomes.items():
        label, detail = classify(
            outcome,
            reverted_run.outcomes.get(nodeid),
            collection_error=reverted_run.collection_error,
        )
        rows.append(Row(nodeid, test_file, label, detail, head.keys[nodeid] in touched))
    return rows


def verify_one(test_id: str, paths: list[str], *, mb: str, python: str) -> int:
    """scripts/verify-red.sh: 0 = red without the fix, 1 = passes anyway, 2 = no claim."""
    targets = plan(paths, mb)
    check_imports_here(python, paths)
    if not targets:
        print(
            f"verify-red: {' '.join(paths)} are identical at the merge base ({mb}) -- nothing"
            " was reverted, so this proves nothing",
            file=sys.stderr,
        )
        return 2
    with reverted(targets):
        code, _ = _run(_pytest(python, test_id), {**os.environ, **_RUN_ENV}, None)
    if code == 0:
        print(
            f"verify-red: {test_id} PASSED without the fix -- it does not test the change",
            file=sys.stderr,
        )
        return 1
    if code in (4, 5):  # usage error (no such node id), no tests collected
        print(
            f"verify-red: pytest exited {code} for {test_id} (no such test, or nothing"
            " collected) -- no claim",
            file=sys.stderr,
        )
        return 2
    print(f"verify-red: {test_id} fails without the fix (as it should)")
    return 0


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


def _resolve_base(given: str | None) -> str:
    """--base, else $VERIFY_RED_BASE, else origin/dev; `dev` if that does not resolve."""
    base = given or os.environ.get("VERIFY_RED_BASE") or "origin/dev"
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "-q", f"{base}^{{commit}}"], capture_output=True
    )
    return base if probe.returncode == 0 or given else "dev"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--base", help="the integration ref or the PR's base sha")
    parser.add_argument("--python", default=os.environ.get("VERIFY_RED_PYTHON", sys.executable))
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds per pytest run"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="seconds for all runs; files it cannot cover become rows (CI: under the job timeout)",
    )
    parser.add_argument(
        "--test", help="one pytest node id: revert the named files, run it, exit 0/1/2"
    )
    parser.add_argument("impl", nargs="*", help="with --test: the implementation files to revert")
    args = parser.parse_args(argv)
    start = time.monotonic()

    def remaining() -> float | None:
        return None if args.budget is None else args.budget - (time.monotonic() - start)

    # Python's default SIGTERM/SIGHUP/SIGQUIT end the process without unwinding;
    # raise instead, so _run kills its child and `reverted` restores the tree.
    for sig in ENDING_SIGNALS:
        signal.signal(sig, _terminated)
    try:
        mb = _git("merge-base", _resolve_base(args.base), "HEAD").strip()
        if args.test:
            if not args.impl:
                raise InfraError("name the implementation files to revert")
            return verify_one(args.test, args.impl, mb=mb, python=args.python)
        return verify_pr(mb, args.python, Sink(args.summary), args.timeout, remaining)
    except InfraError as exc:
        print(f"verify-red: could not run: {exc}", file=sys.stderr)
        return 2


def verify_pr(
    mb: str,
    python: str,
    sink: Sink,
    timeout: float,
    remaining: Callable[[], float | None],
) -> int:
    """The CI job: every changed test file, a table row per test."""
    tests, impl = changed_since(mb)
    if not tests or not impl:
        sink.write(render_nothing(tests, impl))
        if impl and not tests:
            print(NO_TEST_WARNING, flush=True)
        return 0
    targets = plan(impl, mb)  # refuses uncommitted state before anything runs
    check_imports_here(python, impl)
    sink.write(render_header(impl, mb))
    with tempfile.TemporaryDirectory(prefix="verify-red-") as tmp:
        for i, test_file in enumerate(tests):
            rows = verify_file(
                test_file,
                i,
                mb=mb,
                targets=targets,
                python=python,
                tmp=Path(tmp),
                timeout=timeout,
                remaining=remaining,
            )
            sink.write(render_file(test_file, rows))
            for line in annotations(rows):
                print(line, flush=True)
    sink.write(LEGEND + "\n")
    return 0


# A cancelled job or `kill` (TERM), the terminal closing or SSH dropping (HUP),
# Ctrl-\ (QUIT): each ends the run as SystemExit(128 + signal), through the
# restore. SIGINT is Python's KeyboardInterrupt already. SIGKILL cannot be caught.
ENDING_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)


def _terminated(signum: int, frame: object) -> None:
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    sys.exit(main())
