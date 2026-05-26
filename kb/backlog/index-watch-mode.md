---
id: index-watch-mode
type: backlog_item
title: "pyrite serve --watch: auto-sync index on filesystem changes"
kind: improvement
status: proposed
priority: low
effort: M
tags: [dx, indexing, watch, file-system]
---

## Problem

KB-as-Code promises that markdown is the source of truth: edit a file in
your editor, see it in Pyrite. In practice you have to remember to run
`pyrite index sync` after every hand edit, or the web UI and search show
stale content.

There is no `pyrite index status` either, so the only way to know whether
you've forgotten is to compare file mtimes against the index — which no
one does.

## Solution

1. Add a `--watch` flag to `pyrite serve` (and a standalone `pyrite index
   watch` command) that:
   - Uses `watchdog` (already a transitive dep of several stacks; verify
     before adding)
   - Watches each registered KB's root directory
   - Debounces (200ms) and runs `index sync` for changed files
   - Logs each sync at info level so the user sees activity
2. Add `pyrite index status` — shows count of files modified since last
   index, broken out per KB. Single command, no flags, JSON-format
   supported.
3. Document the workflow in `kb/backlog/README.md` and the getting-started
   doc.

## Acceptance criteria

- `pyrite serve --watch` runs the server and watches files.
- Edits land in the index within ~500ms.
- Removing a file removes the entry from the index.
- `pyrite index status` shows the drift state.
- Works on macOS and Linux. Windows is best-effort.

## Out of scope

- Real-time push to connected web clients (separate feature — websockets).
  This ticket only keeps the server-side index fresh.

## Related

- `fix-pyrite-index-sync-silently-skipping-modified-files` (done) — this
  builds on that fix
- `journalist-onboarding-flow-and-kb-orientation` — onboarding should
  recommend `--watch` for hand-edit workflows
