---
id: scripts-release-py-one-command-from-a-ci-verified-dev-commit-to-a-github-release
title: 'scripts/release.py: one command from a CI-verified dev commit to a GitHub release'
type: backlog_item
tags:
- release
- process
- milestone-0.24.2
kind: feature
status: done
priority: high
assignee: agent:pyrite-worker
effort: M
---

## Theme: `scripts/release.py` — one command from a CI-verified `dev` commit to a GitHub release

Roadmap 0.24.2 DoD item ("a release should be an unremarkable event"). `heavy: no` (the install-from-tag step runs in a temp venv; no browsers). Model: opus.

### Why

v0.24.1 took ten manual steps across two sessions, one of which pushed with `--no-verify` because the pre-push hooks ran fixers over the wrong range. ADR-0032 §3a's release row (install from the tag, Quick Start, Docker, artifacts) has no automation. The maintainer keeps the decision to cut a release; this script makes executing that decision one command with every check in front of the irreversible step.

### Acceptance

1. `scripts/release.py <version>` (e.g. `0.24.2`) with `--dry-run` as the default-safe mode printing every step it would take and stopping before anything irreversible; `--execute` performs them. Steps, in order, each a named function with its own check and a clear failure message:
   a. Preconditions: on a clean checkout of `dev` at `origin/dev`; `pyproject.toml` version equals `<version>`; `CHANGELOG.md` has `## [<version>] - YYYY-MM-DD` (today) with content, and `[Unreleased]` is empty or absent below it; no open PRs labelled `release-blocker` (create the label if absent, document it).
   b. CI: the run for `origin/dev`'s SHA in `.github/workflows/ci.yml` is `success` (`gh run list --branch dev --commit <sha>`); if none exists or it is running, wait with a timeout (`--wait-ci`), never dispatch a new one silently.
   c. Release layer, before the tag exists (ADR-0032 §3a): install from the SHA into a fresh temp venv (`uv venv` + `uv pip install "pyrite[server,cli] @ git+https://github.com/markramm/pyrite@<sha>"`), run `scripts/run_tutorial.sh` against that install (it exists; it runs the Quick Start), `pyrite --version` equals `<version>`; Docker image build if `docker` is available (skip with a loud note if not — the maintainer's machine cannot verify it, per the roadmap).
   d. Fast-forward `main` to the SHA (`git push origin <sha>:refs/heads/main` — the ruleset allows only fast-forward), tag `v<version>` on it, push the tag, `gh release create v<version>` with notes from the CHANGELOG section plus the contributors line the release-runbook specifies (every outside author of a merged PR since the previous tag).
   e. Post-release: open the next `[Unreleased]` section in `CHANGELOG.md` and bump `pyproject.toml` to the next patch `.dev0` (or leave as documented in the runbook — follow `.claude/skills/pyrite-conductor/release-runbook.md` and update the runbook to say "run scripts/release.py" where it lists the manual steps).
2. The script never pushes `--no-verify`, never force-pushes, never deletes; it refuses if `git status` is dirty; every irreversible step prints the exact command first and, without `--execute`, prints it instead of running it.
3. Tests in `tests/test_release_script.py` for the pure parts: version/changelog validation (fixtures with good and bad `CHANGELOG.md`/`pyproject.toml`), notes extraction (the section, the contributors line), the CI-status decision given mocked `gh` JSON, the step ordering (an irreversible step never precedes a check). No test performs network or git pushes; `--dry-run` against this repo is exercised in a test with the network calls monkeypatched.
4. `docs/` or the runbook documents the one command and what each step checks; CHANGELOG line.

### Touches

Existing: `.claude/skills/pyrite-conductor/release-runbook.md` (replace the manual list with the script and keep the site mapping), `CHANGELOG.md`, `docs/` (one page or a section), `pyproject.toml` only if a dependency for the script is needed (prefer none — `subprocess` + `gh`).
New: `scripts/release.py`, `tests/test_release_script.py`.
Out of scope: the Docker workflow itself, PyPI publishing (no name chosen — `choose-a-pypi-distribution-name…`), the deploy steps (deploy.sh stays as is), CHANGELOG fragments (separate quality item).
