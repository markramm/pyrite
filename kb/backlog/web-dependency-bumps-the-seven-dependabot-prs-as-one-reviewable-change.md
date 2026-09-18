---
id: web-dependency-bumps-the-seven-dependabot-prs-as-one-reviewable-change
title: 'Web dependency bumps: the seven Dependabot PRs as one reviewable change'
type: backlog_item
tags:
- web
- dependencies
- chore
kind: task
status: in_progress
priority: medium
assignee: agent:pyrite-worker
effort: S
---

## Theme: web dependency bumps — the seven Dependabot PRs as one reviewable change

Supersedes Dependabot PRs #23 #24 #25 #26 #27 #28 #29 (all `web/`, all `MERGEABLE`, all `BEHIND` since 2026-09-18). `heavy: no` (build + unit + svelte-check; no browser suite — the Playwright slot is held by A.1). Model: sonnet.

### Why

Seven separate bumps to `web/package.json` would each put the others `BEHIND` and re-run the frontend gate seven times; and a `@sveltejs/kit` 2.53 → 2.70 bump can move the DOM the new Playwright specs assert on, so it lands as one change, verified once, before packages F/G are dispatched.

### Acceptance

1. In `web/`: apply exactly the seven version changes the Dependabot PRs propose (read each with `gh pr diff N -- web/package.json`): undici 7.22.0→7.29.1, @vitest/mocker + vitest (#24, #26 → the same vitest 4.1.11), nanoid 3.3.11→3.3.19, @sveltejs/kit 2.53.0→2.70.3, @tiptap/core 3.20.0→3.31.3, devalue 5.6.3→5.9.2. `npm install` (or `npm update` to those exact versions) so `package-lock.json` is regenerated consistently; no other dependency moves unless the lockfile forces a transitive bump — list any that do.
2. `npm ci` from the new lockfile in a clean `node_modules` (delete it first), then `npm run build`, `npm run test:unit`, `npm run check` — all green; report counts (files checked, warnings before vs after — the 23 pre-existing a11y warnings are known).
3. `npm audit --omit=dev` before and after: the count of advisories the bumps close (the repo shows 53 alerts; say how many this closes).
4. One commit per logical group is fine (runtime deps, dev deps) or one commit; message says which PRs it supersedes. CHANGELOG line under `[Unreleased]` (dependency bumps; note any user-visible change the changelogs of `@sveltejs/kit`/`@tiptap/core` list).
5. Do NOT run the Playwright suite (another worker holds the only slot); say so in the report, and note that the conductor will run it once after merge to confirm the stable failing set is unchanged.
6. After the PR is opened and reviewed, the conductor closes #23–#29 with a comment naming this PR — you do not close them.

### Touches

Existing: `web/package.json`, `web/package-lock.json`, `CHANGELOG.md`. New: none.
Out of scope: any source change under `web/src`; the Python side; Playwright config or specs.
