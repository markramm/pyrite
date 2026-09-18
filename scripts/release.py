#!/usr/bin/env python3
"""One command from a CI-verified `dev` commit to a GitHub release.

    scripts/release.py 0.24.2              # dry run: prints every step, changes nothing
    scripts/release.py 0.24.2 --execute    # actually cuts the release
    scripts/release.py 0.24.2 --wait-ci 20 # wait up to 20 min for a pending CI run

v0.24.1 took ten manual steps across two sessions, one of which pushed with
`--no-verify` because the pre-push hooks ran fixers over the wrong range. The
maintainer keeps the *decision* to cut a release; this script makes executing
that decision one command, with every check in front of the first thing that
cannot be undone.

The order is the point (ADR-0032 §3a). Five steps, and the first two that can
change the world come last:

  a. preconditions  -- clean `dev` at `origin/dev`; the version in
                       pyproject.toml is <version>; CHANGELOG has a dated
                       section with content and no stranded `[Unreleased]`
                       entries; no open PR labelled `release-blocker`
  b. ci             -- the REQUIRED checks for that exact SHA concluded
                       `success` (default `gate`; `--require-check` to change
                       it). Checks not named are advisory and never block --
                       the breadth jobs that run after the merge gate must not
                       hold a tag. Never starts a run; waits, with `--wait-ci`.
  c. release layer  -- what a *user* gets, checked before the tag exists:
                       install from the SHA into a fresh temp venv with `uv`,
                       `pyrite --version`, and the getting-started tutorial run
                       against that install. Docker build if docker is there,
                       a loud skip if not.
  d. publish        -- IRREVERSIBLE. Fast-forward `main` to the SHA, tag it,
                       push the tag, `gh release create` with the CHANGELOG
                       section plus the contributors line.
  e. post-release   -- IRREVERSIBLE (a commit on dev). Reopen `[Unreleased]`.

Safety rules, pinned by tests/test_release_script.py:

  * `--dry-run` is the default. `--execute` is the only way anything is written.
  * It never passes `--no-verify`, never force-pushes, never deletes a ref.
  * It refuses a dirty checkout, a branch other than `dev`, or a `dev` that is
    not exactly `origin/dev`.
  * Every irreversible command is printed verbatim before it runs, and printed
    *instead of* running without `--execute`.
  * `gh` reads are allowed; `gh` writes are dry-run-printed. The
    `release-blocker` label is a documented prerequisite -- see the runbook.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REMOTE_URL = "https://github.com/markramm/pyrite"
MAINTAINER = "markramm"
BLOCKER_LABEL = "release-blocker"
REPO_SLUG = f"{MAINTAINER}/pyrite"

SEMVER = re.compile(r"^\d+\.\d+\.\d+([-.][0-9A-Za-z.]+)?$")

# The checks a release waits on, by name. `gate` is the required check on dev
# and main: it needs the jobs that must pass and fails on any of their
# failures, so requiring it requires them. Advisory checks (breadth jobs that
# run after the gate) are deliberately not here -- see ci_decision.
DEFAULT_REQUIRED_CHECKS = ("gate",)

CI_PASSED = "passed"
CI_FAILED = "failed"
CI_PENDING = "pending"
CI_MISSING = "missing"


class ReleaseError(Exception):
    """A check said no. The message is what the maintainer needs to do."""


# ---------------------------------------------------------------------------
# process plumbing -- one seam (`_check_output`) so tests never shell out
# ---------------------------------------------------------------------------


def _check_output(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> str:
    """Run a READ-ONLY command and return its stdout. The single subprocess
    seam in this module: tests monkeypatch this and nothing escapes."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ReleaseError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"{proc.stdout}\n{proc.stderr}".rstrip()
        )
    return proc.stdout


def _gh_json(cmd: list[str]) -> list | dict:
    raw = _check_output(cmd).strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"could not parse JSON from {' '.join(cmd)}: {exc}") from exc


class Runner:
    """Prints every command; runs the writes only with `--execute`.

    A "write" is anything that changes the world outside this process: a push,
    a tag, `gh release create`, a commit. Reads go through `_check_output`
    directly -- they are safe in both modes and the checks need their answers.
    """

    def __init__(self, execute: bool):
        self.execute = execute
        # Every write this run planned, in order -- printed or performed. The
        # safety tests read it back and assert what was composed, not what the
        # source text happens to say.
        self.planned: list[list[str]] = []

    def run_write(self, cmd: list[str], cwd: Path | None = None) -> str | None:
        self.planned.append(list(cmd))
        # shlex.join, not " ".join: the maintainer pastes these lines into a
        # shell, and an unquoted `--description Must not ship in the next
        # release` is five arguments there and one here.
        rendered = shlex.join(cmd)
        if not self.execute:
            print(f"    WOULD RUN: {rendered}")
            return None
        print(f"    RUN: {rendered}")
        return _check_output(cmd, cwd=cwd)

    def note(self, message: str) -> None:
        print(f"    {message}")


# ---------------------------------------------------------------------------
# git reads
# ---------------------------------------------------------------------------


def git_status_porcelain(repo: Path) -> str:
    return _check_output(["git", "-C", str(repo), "status", "--porcelain"]).strip()


def current_branch(repo: Path) -> str:
    return _check_output(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"]).strip()


def rev_parse(repo: Path, ref: str) -> str:
    return _check_output(["git", "-C", str(repo), "rev-parse", ref]).strip()


# ---------------------------------------------------------------------------
# version + CHANGELOG (pure; the bulk of the tests)
# ---------------------------------------------------------------------------


def normalize_version(version: str) -> str:
    """Accept `0.24.2`, refuse `v0.24.2` and `0.24`.

    A `v` prefix is refused rather than stripped: the tag is `v<version>` and
    the pyproject version is `<version>`, and quietly accepting both spellings
    is how one of them ends up wrong.
    """
    if not SEMVER.match(version):
        raise ReleaseError(
            f"{version!r} is not a version: give X.Y.Z with no 'v' prefix "
            "(the tag gets the v, you do not)."
        )
    return version


def read_pyproject_version(repo: Path) -> str:
    path = repo / "pyproject.toml"
    if not path.exists():
        raise ReleaseError(f"no pyproject.toml at {path}")
    return tomllib.loads(path.read_text())["project"]["version"]


def check_version_matches(repo: Path, version: str) -> None:
    declared = read_pyproject_version(repo)
    if declared != version:
        raise ReleaseError(
            f"pyproject.toml says version = {declared!r} but you asked to release "
            f"{version!r}. The release commit belongs on dev: bump pyproject.toml "
            "and date the CHANGELOG section there first."
        )


def _section_span(text: str, version: str) -> tuple[re.Match, int]:
    """Return the heading match for `## [<version>]` and where its body ends."""
    heading = re.search(rf"^##\s*\[{re.escape(version)}\](?P<rest>[^\n]*)$", text, re.M)
    if not heading:
        raise ReleaseError(
            f"CHANGELOG.md has no `## [{version}]` section. Add one on dev, "
            f"dated today: `## [{version}] - {date.today().isoformat()}`."
        )
    following = re.compile(r"^##\s", re.M).search(text, heading.end())
    return heading, following.start() if following else len(text)


def check_changelog(repo: Path, version: str) -> None:
    """The section exists, is dated today, has content, and nothing is
    stranded under `[Unreleased]` below it."""
    text = (repo / "CHANGELOG.md").read_text()
    heading, end = _section_span(text, version)

    rest = heading.group("rest")
    dated = re.search(r"(\d{4}-\d{2}-\d{2})", rest)
    if not dated:
        raise ReleaseError(
            f"`## [{version}]` is undated. The runbook wants "
            f"`## [{version}] - YYYY-MM-DD` so the release notes and the tag agree."
        )
    if dated.group(1) != date.today().isoformat():
        raise ReleaseError(
            f"`## [{version}]` is dated {dated.group(1)}, today is "
            f"{date.today().isoformat()}. Re-date it on dev (and let CI pass on "
            "that commit) before releasing."
        )

    body = text[heading.end() : end].strip()
    if not body:
        raise ReleaseError(
            f"`## [{version}]` has no content. A release with empty notes tells "
            "users nothing; write the section on dev first."
        )

    unreleased = re.search(r"^##\s*\[Unreleased\][^\n]*$", text, re.M)
    if unreleased:
        u_end = re.compile(r"^##\s", re.M).search(text, unreleased.end())
        u_body = text[unreleased.end() : u_end.start() if u_end else len(text)].strip()
        if u_body:
            raise ReleaseError(
                "`## [Unreleased]` still has entries. Either they ship in "
                f"{version} (move them into its section) or they do not (move "
                "them to a later release) -- as written they would be silently "
                "left out of the notes."
            )


def release_notes_for(repo: Path, version: str) -> str:
    """The body of this version's CHANGELOG section, and nothing else.

    THE seam for where release notes come from. A later theme moves the source
    to per-PR fragments under `changelog.d/`; when it does, this function's
    body changes and nothing above it needs to. Keep it the only place that
    knows the notes' origin.
    """
    text = (repo / "CHANGELOG.md").read_text()
    heading, end = _section_span(text, version)
    return text[heading.end() : end].strip() + "\n"


def contributors_line(logins: list[str]) -> str | None:
    """Every outside author of a merged PR since the previous tag, credited.

    Contributors are why the project is not a solo project; the runbook says
    to say so.
    """
    outside = sorted(
        {
            login
            for login in logins
            if login and login != MAINTAINER and "dependabot" not in login.lower()
        }
    )
    if not outside:
        return None
    names = ", ".join(f"@{login}" for login in outside)
    return f"Thanks to {names} for their contributions."


def compose_notes(repo: Path, version: str, logins: list[str]) -> str:
    notes = release_notes_for(repo, version)
    line = contributors_line(logins)
    if line:
        notes = notes.rstrip() + "\n\n" + line + "\n"
    return notes


# ---------------------------------------------------------------------------
# CI decision (pure, over `gh run list` JSON)
# ---------------------------------------------------------------------------


def _matches(check_name: str, required: str) -> bool:
    """`test` must match the matrix leg `test (3.12)` and the bare `test` a
    skipped matrix reports -- requiring one by name cannot mean requiring the
    exact string, or a docs-only run hangs the release the way it hung PRs."""
    return check_name == required or check_name.startswith(f"{required} (")


def ci_decision(checks: list[dict], required: tuple[str, ...] | None = None) -> str:
    """Verdict over the NAMED checks a release requires, for one SHA.

    Gating on "every check on the commit" is wrong and would get worse: `e2e`
    runs on pushes to `main` and is deliberately *not* in `gate`'s needs
    (ADR-0032 §3a keeps breadth out of the merge gate), so a red or slow e2e
    must not block a tag. What must be green is `gate` -- and `gate` is green
    only when the jobs it needs are.

    Conservative within that set: a required check still running outranks a
    sibling that passed, and any non-success conclusion is a failure. A
    `skipped` check passes (ADR-0032: the classifier saying "nothing to test
    here"). A required check that is absent entirely is CI_MISSING, not a pass.

    This function only reads a verdict; it cannot start a run.
    """
    required = required or DEFAULT_REQUIRED_CHECKS
    if not checks:
        return CI_MISSING

    verdicts = []
    for name in required:
        matching = [c for c in checks if _matches(c.get("name", ""), name)]
        if not matching:
            return CI_MISSING
        if any(c.get("status") != "completed" for c in matching):
            verdicts.append(CI_PENDING)
        elif any(c.get("conclusion") not in ("success", "skipped") for c in matching):
            verdicts.append(CI_FAILED)
        else:
            verdicts.append(CI_PASSED)

    if CI_FAILED in verdicts:
        return CI_FAILED
    if CI_PENDING in verdicts:
        return CI_PENDING
    return CI_PASSED


def check_no_release_blockers(prs: list[dict]) -> None:
    if prs:
        listed = ", ".join(f"#{pr['number']} {pr.get('title', '')}".strip() for pr in prs)
        raise ReleaseError(
            f"open PR(s) labelled {BLOCKER_LABEL}: {listed}. Land or unlabel them before releasing."
        )


def check_clean_checkout(repo: Path) -> str:
    """Clean `dev`, exactly at `origin/dev`. Returns the SHA to release."""
    dirty = git_status_porcelain(repo)
    if dirty:
        raise ReleaseError(
            "the checkout is dirty -- uncommitted changes would not be in the "
            f"released commit:\n{dirty}"
        )
    branch = current_branch(repo)
    if branch != "dev":
        raise ReleaseError(
            f"on branch {branch!r}; a release is cut from dev. "
            "`git checkout dev && git pull --ff-only` first."
        )
    head = rev_parse(repo, "HEAD")
    upstream = rev_parse(repo, "origin/dev")
    if head != upstream:
        raise ReleaseError(
            f"HEAD ({head[:12]}) is not origin/dev ({upstream[:12]}). "
            "Only a commit CI has already seen may be released: "
            "`git fetch origin && git pull --ff-only`."
        )
    return head


# ---------------------------------------------------------------------------
# the five steps
# ---------------------------------------------------------------------------


@dataclass
class Context:
    repo: Path
    version: str
    runner: Runner
    wait_ci_minutes: int
    required_checks: tuple[str, ...] = DEFAULT_REQUIRED_CHECKS
    skip_install_check: bool = False
    rehearse_install_check: bool = False
    sha: str = ""
    notes: str = ""


@dataclass
class Step:
    key: str
    name: str
    irreversible: bool
    run: Callable[[Context], None]


def step_preconditions(ctx: Context) -> None:
    ctx.sha = check_clean_checkout(ctx.repo)
    ctx.runner.note(f"dev is clean at origin/dev: {ctx.sha}")

    check_version_matches(ctx.repo, ctx.version)
    ctx.runner.note(f"pyproject.toml version == {ctx.version}")

    check_changelog(ctx.repo, ctx.version)
    ctx.runner.note(f"CHANGELOG has `## [{ctx.version}] - {date.today().isoformat()}` with content")

    # `--repo` on every gh call: it otherwise infers the repo from the cwd,
    # which is not necessarily the repo being released.
    labels = _gh_json(
        ["gh", "label", "list", "--repo", REPO_SLUG, "--json", "name", "--limit", "200"]
    )
    known = {entry.get("name") for entry in labels} if isinstance(labels, list) else set()
    if BLOCKER_LABEL not in known:
        ctx.runner.note(
            f"NOTE: the {BLOCKER_LABEL!r} label does not exist in this repo. "
            "It is a prerequisite, not something this script creates:"
        )
        ctx.runner.run_write(
            [
                "gh",
                "label",
                "create",
                BLOCKER_LABEL,
                "--repo",
                REPO_SLUG,
                "--description",
                "Must not ship in the next release",
                "--color",
                "B60205",
            ]
        )
    else:
        blockers = _gh_json(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                REPO_SLUG,
                "--state",
                "open",
                "--label",
                BLOCKER_LABEL,
                "--json",
                "number,title",
            ]
        )
        check_no_release_blockers(blockers if isinstance(blockers, list) else [])
        ctx.runner.note(f"no open PRs labelled {BLOCKER_LABEL}")


def _checks_for(sha: str) -> list[dict]:
    """The check runs GitHub reports for a commit, by name.

    Check runs, not workflow runs: what a release waits on is the named check
    `gate`, which is a job inside ci.yml, and `gh run list` only knows about
    the workflow as a whole.
    """
    try:
        payload = _gh_json(["gh", "api", f"repos/{REPO_SLUG}/commits/{sha}/check-runs"])
    except ReleaseError as exc:
        # The likeliest real failure is a commit that was never pushed, and the
        # API answers 422 "No commit found". That is exactly CI_MISSING -- the
        # caller's advice ("push it to dev and let CI run") is what you need.
        # Anything else (auth, network) is a genuine error and must surface.
        if "No commit found" in str(exc):
            return []
        raise
    if isinstance(payload, dict):
        runs = payload.get("check_runs", [])
        return runs if isinstance(runs, list) else []
    return []


def _describe(checks: list[dict], required: tuple[str, ...]) -> str:
    relevant = [c for c in checks if any(_matches(c.get("name", ""), r) for r in required)]
    return (
        ", ".join(f"{c.get('name')}={c.get('conclusion') or c.get('status')}" for c in relevant)
        or "none"
    )


def step_ci(ctx: Context) -> None:
    required = tuple(ctx.required_checks)
    deadline = time.monotonic() + ctx.wait_ci_minutes * 60
    while True:
        checks = _checks_for(ctx.sha)
        verdict = ci_decision(checks, required=required)
        if verdict == CI_PASSED:
            ctx.runner.note(
                f"required check(s) green on {ctx.sha[:12]}: {_describe(checks, required)}"
            )
            other = [
                c.get("name")
                for c in checks
                if not any(_matches(c.get("name", ""), r) for r in required)
                and c.get("conclusion") not in ("success", "skipped", None)
            ]
            if other:
                ctx.runner.note(
                    f"(advisory, not blocking: {', '.join(other)} -- not in "
                    "--require-check, so it does not hold the release)"
                )
            return
        if verdict == CI_FAILED:
            raise ReleaseError(
                f"a required check is not green on {ctx.sha[:12]}: "
                f"{_describe(checks, required)}. Fix it on dev; the tagged "
                "commit must be one CI passed."
            )
        if verdict == CI_MISSING:
            raise ReleaseError(
                f"no run of {', '.join(required)} exists for {ctx.sha[:12]}. Push the "
                "commit to dev and let CI run -- this script never starts one, because "
                "a run it started is not the run the merge gate saw."
            )
        # pending
        if time.monotonic() >= deadline:
            raise ReleaseError(
                f"a required check is still running on {ctx.sha[:12]} after "
                f"{ctx.wait_ci_minutes} min: {_describe(checks, required)}. "
                "Re-run with a longer --wait-ci, or wait and try again."
            )
        ctx.runner.note(f"required check(s) still running on {ctx.sha[:12]}; waiting 30s")
        time.sleep(30)


def step_release_layer(ctx: Context) -> None:
    """What a user actually gets, verified before the tag exists (ADR-0032 §3a).

    Installs from the SHA -- not the tag, which does not exist yet -- into a
    throwaway venv, checks `pyrite --version`, and runs the getting-started
    tutorial against that install.

    Nothing here is irreversible: it writes only to a temp directory. It is
    still minutes of network and CPU, so a dry run prints the commands instead
    of running them; `--install-check` rehearses it for real without
    `--execute`, which is how you test this step before release day.
    """
    if ctx.skip_install_check:
        ctx.runner.note("SKIPPED (--skip-install-check): nothing verified about the install")
        return

    if not (ctx.runner.execute or ctx.rehearse_install_check):
        spec = f"pyrite[server,cli] @ git+{REMOTE_URL}@{ctx.sha}"
        print("    WOULD RUN: uv venv <tmp>")
        print(f'    WOULD RUN: uv pip install --python <tmp>/bin/python "{spec}"')
        print(f"    WOULD RUN: <tmp>/bin/pyrite --version    (must contain {ctx.version})")
        print("    WOULD RUN: PYRITE_TUTORIAL_VENV=<tmp> scripts/run_tutorial.sh")
        print(f"    WOULD RUN: docker build -t pyrite:{ctx.version} .    (if docker is present)")
        ctx.runner.note(
            "pass --install-check to actually run this step in a dry run "
            "(minutes: a real install from GitHub plus the tutorial)"
        )
        return

    if not shutil.which("uv"):
        raise ReleaseError(
            "uv is not on PATH; the install check needs it "
            "(https://docs.astral.sh/uv/). Install it, or pass "
            "--skip-install-check and do the runbook's clean-venv check by hand."
        )

    venv = Path(tempfile.mkdtemp(prefix="pyrite-release-venv-"))
    spec = f"pyrite[server,cli] @ git+{REMOTE_URL}@{ctx.sha}"
    try:
        ctx.runner.note(f"temp venv: {venv}")
        print(f"    RUN: uv venv {venv}")
        _check_output(["uv", "venv", str(venv)])
        print(f'    RUN: uv pip install --python {venv}/bin/python "{spec}"')
        _check_output(["uv", "pip", "install", "--python", str(venv / "bin" / "python"), spec])

        reported = _check_output([str(venv / "bin" / "pyrite"), "--version"]).strip()
        if ctx.version not in reported:
            raise ReleaseError(
                f"the install from {ctx.sha[:12]} reports {reported!r}, which does "
                f"not contain {ctx.version}. A user installing the tag would get "
                "the wrong version."
            )
        ctx.runner.note(f"`pyrite --version` from the install: {reported}")

        env = dict(os.environ)
        env["PYRITE_TUTORIAL_VENV"] = str(venv)
        print(
            f"    RUN: PYRITE_TUTORIAL_VENV={venv} scripts/run_tutorial.sh"
            "   (docs/getting-started.md against the install)"
        )
        _check_output([str(ctx.repo / "scripts" / "run_tutorial.sh")], cwd=ctx.repo, env=env)
        ctx.runner.note("getting-started tutorial ran clean against the install")
    finally:
        shutil.rmtree(venv, ignore_errors=True)

    dockerfile = ctx.repo / "Dockerfile"
    if not shutil.which("docker"):
        ctx.runner.note(
            "!! DOCKER NOT VERIFIED: `docker` is not on PATH, so the image in "
            "the release notes is unproven on this machine. Say so in the notes, "
            "or run the build somewhere with docker."
        )
    elif not dockerfile.exists():
        ctx.runner.note(f"!! DOCKER NOT VERIFIED: no Dockerfile at {dockerfile}")
    else:
        print(f"    RUN: docker build -t pyrite:{ctx.version} .")
        _check_output(["docker", "build", "-t", f"pyrite:{ctx.version}", "."], cwd=ctx.repo)
        ctx.runner.note(f"docker image pyrite:{ctx.version} built")


def _contributor_logins(since_tag: str | None) -> list[str]:
    if not since_tag:
        return []
    merged_at = _check_output(
        [
            "gh",
            "api",
            f"repos/{REPO_SLUG}/releases/tags/{since_tag}",
            "--jq",
            ".published_at",
        ]
    ).strip()
    if not merged_at:
        return []
    prs = _gh_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            REPO_SLUG,
            "--state",
            "merged",
            "--base",
            "dev",
            "--search",
            f"merged:>{merged_at[:10]}",
            "--limit",
            "200",
            "--json",
            "author",
        ]
    )
    if not isinstance(prs, list):
        return []
    return [pr.get("author", {}).get("login", "") for pr in prs]


def _previous_tag(repo: Path) -> str | None:
    try:
        return (
            _check_output(["git", "-C", str(repo), "describe", "--tags", "--abbrev=0"]).strip()
            or None
        )
    except ReleaseError:
        return None


def step_publish(ctx: Context) -> None:
    """IRREVERSIBLE. Fast-forward main, tag, push the tag, cut the release.

    `git push origin <sha>:refs/heads/main` is a fast-forward-only push: the
    ruleset on main refuses anything else, which is the safety net. No force,
    no lease, no delete.
    """
    tag = f"v{ctx.version}"
    logins = _contributor_logins(_previous_tag(ctx.repo))
    ctx.notes = compose_notes(ctx.repo, ctx.version, logins)
    line = contributors_line(logins)
    ctx.runner.note(
        "release notes: the CHANGELOG section"
        + (f" + {line}" if line else " (no outside contributors this cycle)")
    )

    ctx.runner.run_write(
        ["git", "-C", str(ctx.repo), "push", "origin", f"{ctx.sha}:refs/heads/main"]
    )
    ctx.runner.run_write(
        [
            "git",
            "-C",
            str(ctx.repo),
            "tag",
            "-a",
            tag,
            "-m",
            f"{tag}: see CHANGELOG.md",
            ctx.sha,
        ]
    )
    ctx.runner.run_write(["git", "-C", str(ctx.repo), "push", "origin", tag])

    notes_file = Path(tempfile.mkdtemp(prefix="pyrite-release-notes-")) / "notes.md"
    notes_file.write_text(ctx.notes)
    # --repo explicitly: `gh` otherwise infers it from the cwd, which is not
    # necessarily the repo being released, and a release cut against the wrong
    # repo is not undoable.
    ctx.runner.run_write(
        [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            REPO_SLUG,
            "--title",
            tag,
            "--notes-file",
            str(notes_file),
        ]
    )
    ctx.runner.note(f"(notes written to {notes_file})")


def step_post_release(ctx: Context) -> None:
    """IRREVERSIBLE (a commit on dev). Reopen `[Unreleased]`.

    pyproject.toml is deliberately NOT bumped to a `.dev0`: `pyrite.__version__`
    reads it and `tests/test_version_consistency.py` pins it, so dev between
    releases reports the last released version -- the runbook's long-standing
    behaviour. The next release's bump is part of its own release commit.
    """
    changelog = ctx.repo / "CHANGELOG.md"
    text = changelog.read_text()
    if re.search(r"^##\s*\[Unreleased\]", text, re.M):
        ctx.runner.note("CHANGELOG already has an `[Unreleased]` section; nothing to do")
        return

    marker = re.search(rf"^##\s*\[{re.escape(ctx.version)}\]", text, re.M)
    if not marker:
        raise ReleaseError("cannot reopen [Unreleased]: the released section vanished")
    updated = text[: marker.start()] + "## [Unreleased]\n\n" + text[marker.start() :]

    if ctx.runner.execute:
        changelog.write_text(updated)
        print("    RUN: write CHANGELOG.md with a fresh `## [Unreleased]`")
    else:
        print("    WOULD RUN: write CHANGELOG.md with a fresh `## [Unreleased]`")
    ctx.runner.run_write(
        [
            "git",
            "-C",
            str(ctx.repo),
            "commit",
            "-m",
            f"chore: open [Unreleased] after v{ctx.version}",
            "--",
            "CHANGELOG.md",
        ]
    )
    ctx.runner.note(
        "push it as a PR to dev like any other change (the ruleset refuses a "
        "direct push): `git push -u origin <branch> && gh pr create --base dev --fill`"
    )


STEPS: list[Step] = [
    Step("preconditions", "a. preconditions", False, step_preconditions),
    Step("ci", "b. CI is green on this SHA", False, step_ci),
    Step("release_layer", "c. release layer: install, tutorial, docker", False, step_release_layer),
    Step("publish", "d. main, tag, GitHub release", True, step_publish),
    Step("post_release", "e. reopen [Unreleased]", True, step_post_release),
]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scripts/release.py",
        description="Cut a Pyrite release from a CI-verified dev commit. "
        "Dry run by default: nothing is written without --execute.",
    )
    parser.add_argument("version", help="the version to release, e.g. 0.24.2 (no 'v')")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--execute",
        action="store_true",
        help="actually do it. Without this, every irreversible command is printed only.",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="the default; accepted so you can say it out loud.",
    )
    parser.add_argument(
        "--require-check",
        action="append",
        metavar="NAME",
        help="a check that must be green before the tag, by name. Repeatable. "
        f"Default: {', '.join(DEFAULT_REQUIRED_CHECKS)}. Checks NOT named here are "
        "advisory and never block the release -- that is deliberate for the breadth "
        "jobs that run after the merge gate.",
    )
    parser.add_argument(
        "--wait-ci",
        type=int,
        default=0,
        metavar="MINUTES",
        help="wait this many minutes for a pending CI run (default: do not wait).",
    )
    parser.add_argument(
        "--skip-install-check",
        action="store_true",
        help="skip step c (the temp-venv install and tutorial run) entirely. Only "
        "when you have done the runbook's clean-venv check by hand.",
    )
    parser.add_argument(
        "--install-check",
        action="store_true",
        help="in a dry run, actually perform step c instead of printing it. Takes "
        "minutes (a real install from GitHub plus the tutorial); harmless.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=REPO,
        help=argparse.SUPPRESS,  # tests only
    )
    args = parser.parse_args(argv)
    # `action="append"` starts at None rather than the default, and giving it a
    # list default would append to it instead of replacing it.
    if not args.require_check:
        args.require_check = list(DEFAULT_REQUIRED_CHECKS)
    return args


def run_release(args: argparse.Namespace) -> tuple[int, Runner]:
    """Walk the steps. Returns the exit code and the Runner, whose `planned`
    list is every write the run printed or performed -- what the safety tests
    inspect."""
    runner = Runner(execute=args.execute)

    try:
        version = normalize_version(args.version)
    except ReleaseError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1, runner

    ctx = Context(
        repo=args.repo,
        version=version,
        runner=runner,
        wait_ci_minutes=args.wait_ci,
        required_checks=tuple(args.require_check),
        skip_install_check=args.skip_install_check,
        rehearse_install_check=args.install_check,
    )

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"pyrite release {version} [{mode}]")
    if not args.execute:
        print(
            "  Dry run: every irreversible command is printed, not run. "
            "Re-run with --execute to cut the release."
        )
    print()

    for step in STEPS:
        marker = " (IRREVERSIBLE)" if step.irreversible else ""
        print(f"  {step.name}{marker}")
        try:
            step.run(ctx)
        except ReleaseError as exc:
            # Piped, stdout block-buffers and stderr does not: without this the
            # failure prints above the header and the step it failed in, which
            # is how it reads in a log or a CI transcript.
            sys.stdout.flush()
            print(f"\nFAIL at {step.key}: {exc}", file=sys.stderr)
            print("Nothing further was attempted.", file=sys.stderr)
            sys.stderr.flush()
            return 1, runner
        print()

    if args.execute:
        print(f"Released v{version}. Deploy with pyrite_deployments/deploy.sh.")
    else:
        print(f"Dry run complete: v{version} looks releasable. Re-run with --execute.")
    return 0, runner


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv) if argv is not None else sys.argv[1:])
    code, _runner = run_release(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
