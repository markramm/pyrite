---
id: installable-from-github-with-a-working-web-ui-package-the-built-frontend
title: 'Installable from GitHub with a working web UI: package the built frontend'
type: backlog_item
tags:
- packaging
- install
- web
- release
- go-to-market
importance: 5
kind: feature
status: proposed
priority: high
effort: M
rank: 0
---

## Problem

PyPI is unreachable (the `pyrite` name is held by a locked account — ADR-0025), so
installing from GitHub is not a workaround, it is the only path. The intended
one-liner for a non-developer:

    uv tool install "pyrite[server,cli] @ git+https://github.com/markramm/pyrite@vX.Y.Z"

`uv tool install` brings its own Python, puts `pyrite`, `pyrite-server`,
`pyrite-read`, `pyrite-admin` on PATH in an isolated venv, and `[server,cli]` is
all wheels (no compiler; `[semantic]` is the torch path and stays optional). Pin a
tag, never a branch.

**Today that install has no web UI, and says nothing about it.** Verified
2026-09-17 against a non-editable install of `6f6311e` in a clean venv:

1. `web/dist` is untracked: `.gitignore` has a bare `dist/`, which matches at any
   depth. A fresh clone has no built frontend, and the Python build never runs npm.
2. Even if it were tracked, `web/` is outside the package:
   `[tool.setuptools.packages.find] include = ["pyrite", "pyrite.*"]`. Nothing
   under `web/` can land in a wheel. `prune web` in MANIFEST.in is a red herring.
3. The server looks for `PYRITE_STATIC_DIR`, else
   `Path(__file__).parent.parent.parent / "web" / "dist"` — which in
   site-packages points at nothing. `if dist_dir.is_dir()` is false, the SPA is
   simply not mounted, and **no warning is logged**. The installed package
   contains 187 `.py` files and exactly two data files
   (`server/templates/*.html`).
4. MANIFEST.in allowlists extensions (`*.py *.yaml *.json *.html *.css *.js`).
   SvelteKit output includes `.woff2`, `.svg`, `.png` and sourcemaps; those would
   be dropped silently — a UI with no fonts or icons and no error.

So the frontend has to live inside the package, at `pyrite/static/`, either way.

## Plan

**Step 1 — commit the built frontend (gets a user running with zero new
infrastructure).** Build `web/dist`, copy to `pyrite/static/`, add a `.gitignore`
negation, `recursive-include pyrite/static *` in MANIFEST.in plus
`[tool.setuptools.package-data]`, and make the server default to the packaged
directory (`PYRITE_STATIC_DIR` still overrides; the dev checkout still prefers
`web/dist` when present). Refresh `pyrite/static/` only in the release commit,
not on every frontend change, to bound the repo growth. A test asserts the
committed build matches the frontend source hash recorded at build time, so a
release cannot ship a stale UI.

**Step 2 — release-attached wheel (when next touching CI).** CI runs
`npm run build`, builds the wheel, attaches it to the GitHub release:

    uv tool install "pyrite[server,cli] @ https://github.com/markramm/pyrite/releases/download/vX.Y.Z/pyrite-X.Y.Z-py3-none-any.whl"

No repo bloat, real artifacts. The URL carries the version (pip parses it from the
wheel filename, so `/releases/latest/download/` cannot help); the install docs
are generated per release. Once this exists, `pyrite/static/` can leave git.

## Acceptance

- [ ] In a clean venv, the one-liner installs and `pyrite-server` serves the SPA
      at `/` with fonts and icons (assert a `.woff2` and an `.svg` return 200).
- [ ] When no static directory is found, the server logs one clear warning that
      says how to get a UI.
- [ ] The release runbook's clean-venv step checks the UI, not just
      `pyrite.__version__`.
- [ ] README Quick Start leads with the `uv tool install` one-liner.

Noted while verifying: `pyrite/storage/alembic.ini` and
`alembic/script.py.mako` are also absent from non-editable installs. Nothing
imports them at runtime (they are migration-authoring tools), so this is
harmless, but it is the same allowlist at work.

Related: [[choose-a-pypi-distribution-name-and-decide-the-fate-of-pyrite-mcp]],
ADR-0031 (`pyrite-core-ui` as an addressable package).

## Groom 2026-09-18 (serial)

Split into three themes after #168 (one Pyrite task at a time; each theme one worker pass and one review). This item stays the parent and closes with the third. Dispatch order and the full groom — acceptance, regimes, touches, model, size — are in each:

1. [[packaged-web-ui-1-the-server-finds-a-packaged-ui-and-warns-when-there-is-none]] — sonnet, S, cold read. `pyrite/server/api.py` only. Independent; ships alone.
2. [[packaged-web-ui-2-the-built-frontend-ships-inside-the-package]] — opus, M, heavy (one npm build, one wheel build), cold read. `.gitignore`, `MANIFEST.in`, `pyproject.toml`, `pyrite/static/`, the build-hash and wheel-contents tests. After 1.
3. [[packaged-web-ui-3-quick-start-leads-with-the-one-liner-and-the-release-checks-the-ui]] — sonnet, S–M, cold read (`scripts/release.py`). After 2, after #140, after the changelog-fragments theme.

The tick-6 groom's open coordination question ("release.py first, or this theme owns the runbook edit") is settled by the split: #140 lands as it is; theme 3 owns the UI check in both `scripts/release.py` and the runbook.
