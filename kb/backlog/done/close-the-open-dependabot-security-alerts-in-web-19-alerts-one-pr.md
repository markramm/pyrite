---
id: close-the-open-dependabot-security-alerts-in-web-19-alerts-one-pr
title: Close the open Dependabot security alerts in web/ (19 alerts, one PR)
type: backlog_item
tags:
- web
- dependencies
- security
- chore
kind: task
status: done
priority: high
assignee: agent:pyrite-worker
effort: S
---

## Theme: close the open Dependabot security alerts in `web/` (19 alerts, one PR)

`heavy: no` (build + unit + svelte-check; no browser suite). Model: sonnet. Follows #142 (same shape, same files).

### Why

After #142 the repository's Dependabot page still shows 19 open alerts, all in `web/package-lock.json`: 6 high (vite ×3 — `server.fs.deny` bypasses and an arbitrary file read via the dev server; postcss ×2 — path traversal / arbitrary file read via source-map auto-loading; picomatch ReDoS), 11 medium (svelte ×6, vite, postcss ×2, picomatch), 2 low (esbuild dev-server file read, cookie out-of-bounds characters). Most are dev-server-only exposures, but the alert count is the first thing a new contributor sees on the repo, and every one has a patched version.

### Acceptance

1. Bump to the first patched versions Dependabot names, or later: `vite` ≥ 7.3.5 (a direct devDependency, `"^6.0.0 || ^7.0.0"` — pin the range so it cannot resolve below 7.3.5), `postcss` ≥ 8.5.23, `picomatch` ≥ 4.0.4, `svelte` ≥ 5.55.7, `esbuild` ≥ 0.28.1 — transitive ones via `npm update <pkg>` / `overrides` only where a direct bump does not pull them; say which mechanism each needed. `cookie` (≥ 0.7.0) sits under `@sveltejs/kit`/`adapter-node` and #142 found it needs a breaking major — if that is still true, leave it, say so, and note it as the one that stays open.
2. `npm ci` from a deleted `node_modules` (use `npx --yes npm@11.19.1` — the machine's npm 11.5.1 has an arborist crash, #142), `npm run build`, `npm run test:unit`, `npm run check` — all green; report counts (the 23 a11y warnings are known).
3. `npm audit --omit=dev` and `npm audit` (with dev) before and after: numbers, and the Dependabot alert count expected to drop to the unfixable remainder — the conductor confirms on the alerts page after merge.
4. One Playwright run is NOT required from you (the slot belongs to #138's fixes); the conductor runs it after merge. A `svelte` 5.x bump can move the DOM — say in the report what svelte's changelog lists between the installed and new versions.
5. CHANGELOG line under `[Unreleased] ### Security` (create the subsection if absent) naming the packages and the advisories closed; the backlog item done via `pyrite update`, `git mv` to `kb/backlog/done/`, `pyrite index sync`.

### Touches

Existing: `web/package.json`, `web/package-lock.json`, `CHANGELOG.md`, the backlog item. New: none.
Out of scope: anything under `web/src`; Python; Playwright config/specs; a major bump of `@sveltejs/kit` or `adapter-node` for `cookie`.
