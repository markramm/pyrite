---
id: packaged-web-ui-2-the-built-frontend-ships-inside-the-package
title: 'Packaged web UI (2/3): the built frontend ships inside the package, with a build-hash test'
type: backlog_item
tags:
- packaging
- install
- web
- release
importance: 5
kind: feature
status: proposed
priority: high
effort: M
rank: 0
---

Second of three themes split from [[installable-from-github-with-a-working-web-ui-package-the-built-frontend]]. The packaging itself: the parent's findings 1, 2 and 4.

## Acceptance

From the parent, verbatim: "In a clean venv, the one-liner installs and `pyrite-server` serves the SPA at `/` with fonts and icons (assert a `.woff2` and an `.svg` return 200)." — and from its plan — "A test asserts the committed build matches the frontend source hash recorded at build time, so a release cannot ship a stale UI." — "Refresh `pyrite/static/` only in the release commit, not on every frontend change, to bound the repo growth."

1. `scripts/build_static.sh` runs `npm ci && npm run build` in `web/`, replaces `pyrite/static/` with `web/dist/`, and writes `pyrite/static/BUILD_HASH` = a hash over the frontend sources (`web/src/**`, `web/static/**`, `web/package-lock.json`, `web/svelte.config.js`, `web/vite.config.ts`).
2. `.gitignore`: a negation so `pyrite/static/**` is tracked while the bare `dist/` rule keeps ignoring `web/dist/`. `MANIFEST.in`: `recursive-include pyrite/static *`. `pyproject.toml`: `[tool.setuptools.package-data]` with `pyrite = ["static/**/*"]` (or equivalent that survives setuptools' glob rules).
3. `tests/test_packaged_static.py`: (a) recomputes the source hash and compares it with `BUILD_HASH`. Because the parent refreshes the build only in the release commit, a stale build on `dev` is the normal state: the comparison **fails** only when `PYRITE_REQUIRE_FRESH_STATIC=1` (set by `scripts/release.py` and the post-tag workflow) and is reported as a warning otherwise. A test proves both modes with a doctored `BUILD_HASH`; (b) builds a wheel into a temp dir and asserts its file list contains `pyrite/static/index.html`, at least one `.woff2`, one `.svg`, one `.js` and one `.css` — this is the test that catches a wrong glob, and it needs no server and no network.
4. A smoke-marked test (`tests/e2e/`, the `smoke` CI job — never the PR matrix) installs that wheel into a clean venv, starts `pyrite-server`, and asserts `/` is the SPA and a `.woff2` and an `.svg` return 200.

## Groom 2026-09-18 (serial)

**Regimes:** a file type the old allowlist would drop (`.woff2`, `.svg`, `.png`, `.map`, `.webmanifest`) present in the wheel; a built chunk over the `check-added-large-files` limit (500 KB, `.pre-commit-config.yaml`) — the commit hook will refuse it, so either the hook gains an `exclude: ^pyrite/static/` or sourcemaps are dropped from the packaged copy; say which, and pin it; an sdist (not only a wheel) carrying the files; `pyrite/static/` absent entirely (fresh clone before the first release build — the package still builds and theme 1's warning fires); `BUILD_HASH` missing or malformed; hash stability across macOS/Linux (sort paths, normalise line endings or hash bytes — state which).

**Touches** — existing: `.gitignore`, `MANIFEST.in`, `pyproject.toml`, `.pre-commit-config.yaml` (only for the large-file exclude), `tests/test_dev_process_config.py` (only if that exclude is pinned). New: `scripts/build_static.sh`, `pyrite/static/**` (generated — reviewed as "output of the script at commit X", not line by line), `tests/test_packaged_static.py`, `tests/e2e/test_packaged_ui_install.py`.

**Sequence:** after theme 1 (criterion 4 needs the packaged directory to be found). `.gitignore` is also edited by outside PR #166 — trivial, theirs to rebase.

**Model:** opus (a wrong negation or glob ships an empty UI silently, and the hash/large-file/sdist regimes are each a way to be plausibly wrong). **heavy: yes** — one `npm ci && npm run build` and one wheel build + clean-venv install; each takes the machine's one slot; no repeated runs. **Cold read:** yes. **Size:** M, ~200 hand-written lines across ~7 files, plus the generated build.

**Out of scope:** step 2 of the parent (release-attached wheel); the PyPI name; any change under `web/src/`; README/runbook (theme 3); wiring `build_static.sh` into `scripts/release.py` (theme 3).
