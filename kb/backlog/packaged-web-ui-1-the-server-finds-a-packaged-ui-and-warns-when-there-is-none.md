---
id: packaged-web-ui-1-the-server-finds-a-packaged-ui-and-warns-when-there-is-none
title: 'Packaged web UI (1/3): the server finds a packaged UI and warns once when there is none'
type: backlog_item
tags:
- packaging
- install
- web
- server
- release
importance: 5
kind: feature
status: proposed
priority: high
effort: S
rank: 0
---

First of three themes split from [[installable-from-github-with-a-working-web-ui-package-the-built-frontend]] (2026-09-18, after #168: one worker pass, one review). This one changes only where the server looks and what it says; it ships alone and is useful alone — today a non-editable install mounts no SPA and logs nothing.

## Acceptance

From the parent, verbatim: "When no static directory is found, the server logs one clear warning that says how to get a UI."

And from its plan: "make the server default to the packaged directory (`PYRITE_STATIC_DIR` still overrides; the dev checkout still prefers `web/dist` when present)".

1. Resolution order, in one function with a docstring stating it: `PYRITE_STATIC_DIR` if set → `<checkout>/web/dist` if it is a directory → the packaged `pyrite/static/` (resolved from the package, e.g. `importlib.resources.files("pyrite") / "static"`) if it holds an `index.html` → none.
2. None → exactly one `logger.warning` at startup naming the three ways to get a UI (install a release that packages it, `cd web && npm run build`, or set `PYRITE_STATIC_DIR`), and the API keeps serving.
3. `PYRITE_STATIC_DIR` set to a path that is not a directory, or has no `index.html`, warns and names the path — it does not silently fall through to another directory.

## Groom 2026-09-18 (serial)

**Regimes:** all four outcomes of the order above, each with a temp directory; `PYRITE_STATIC_DIR=""` (treated as unset — today's code already special-cases it); set-but-missing; a `pyrite/static/` that exists but is empty (a wheel built before theme 2 refreshed it — must warn, not mount an empty SPA that 404s every route); the app factory called twice in one process (tests do) — one warning per app, not an accumulating handler; a site-packages layout (simulate by pointing the resolver at a temp package root — do **not** build a wheel here).

**Touches** — existing: `pyrite/server/api.py` (:928–944, the `dist_dir` block), `pyrite/server/static.py` (docstring only), `docs/configuration.md` (`PYRITE_STATIC_DIR` row). New: `tests/test_static_dir_resolution.py`.

**Sequence:** independent — no open PR touches `api.py`. First of the three.

**Model:** sonnet (three branches and a warning, fully specified). **heavy:** no. **Cold read:** yes — server startup path, and a wrong order silently serves a stale UI from the wrong directory. **Size:** S, ~120 lines.

**Out of scope:** committing a build, `.gitignore`, `MANIFEST.in`, `pyproject.toml` (theme 2); README and the runbook (theme 3); `mount_static`'s routing and containment checks (CodeQL-verified, leave them).
