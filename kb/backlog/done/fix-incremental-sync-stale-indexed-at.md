---
id: fix-incremental-sync-failing-to-reindex-modified-files
title: "`pyrite index sync` reports Updated:0 on modified files; full `index build` is required to reindex"
type: backlog_item
tags: [index, sync, cli, data-quality, incremental-sync]
importance: 5
kind: bug
status: completed
priority: high
effort: S
rank: 0
---

## Problem

`pyrite index sync --kb <kb>` reports `Updated: 0` on files that have been
modified directly on disk (editor, script, another process). The changes are
visible on the filesystem and reflected when queried via `pyrite task status`
on re-parse, but the indexed record (and therefore `pyrite task list` output)
continues to show the pre-change state.

Running a full `pyrite index build --kb <kb>` picks up the changes. This is a
workaround but it invalidates the whole point of an incremental sync.

## Reproductions (2026-04-23 session, cascade-research)

Two independent reproductions observed during a single conductor session:

### Reproduction 1 — direct frontmatter edit

1. Read `notes/draft-the-acceleration-curve-theme-entry-*.md` (task file)
2. Edit frontmatter: changed `status: open` → `status: blocked` + added
   `dependencies: [...]` list with four task IDs
3. Ran `pyrite index sync --kb cascade-research --no-embed` → `Updated: 0`
4. `pyrite task status <id>` still reported `Status: open`, no Dependencies
   line
5. `touch` on the file + re-sync still reported `Updated: 0`
6. `pyrite task update <id> --status blocked` (the sanctioned-path command)
   succeeded, and then `task status` correctly showed both the new status AND
   the dependencies from the frontmatter — which proves pyrite COULD read the
   frontmatter, it just didn't from the sync path

### Reproduction 2 — worker direct-file-edits on cascade-research

Independent worker (agent:claude-opus-4-7-parallel-tick6-c, Doha Bank
jurisdictional correction) edited three cascade-research files (one actor,
one organization, one epic-task-body). Ran `pyrite index sync` multiple
times with `touch` between runs: `Updated: 0` each time. Full
`pyrite index build --kb cascade-research` resolved it.

## Likely cause (hypothesis)

Incremental sync may be using content-hash comparison with a stale
cache, or mtime comparison with a stored-timestamp that is set on read
rather than on write. Candidate locations to investigate:

- `pyrite/storage/repository.py` (loading logic; hash/mtime tracking)
- `pyrite/services/index_service.py` (if it exists; incremental-sync orchestration)

Both reproductions suggest the failure is deterministic, not racy — same
files, same result across multiple sync invocations without intervening
writes-via-CLI.

## Impact

- **Direct frontmatter edits are effectively silently lost** from the index
  perspective until a full rebuild runs. Task-system queries return stale
  state.
- **Worker agents that edit KB files directly** (the common pattern for
  investigation-research and kb-lifecycle skills) hit this bug routinely.
  The workaround (full `index build`) is slow on larger KBs (cascade-timeline
  has 4,888 entries) and wastes the incremental-sync feature.
- **Confusing UX**: `task list` shows `open` while `task status` (after the
  sanctioned update path) shows the real state. An agent reasoning about
  state from `list` will make incorrect decisions.

## Acceptance criteria

- [ ] `pyrite index sync` detects mtime OR content-hash changes on files
      that have been modified since last sync, regardless of how they were
      modified (CLI, direct editor, script, worker agent)
- [ ] Regression test: modify a file via `Path.write_text()`, run sync,
      verify the indexed record reflects the change
- [ ] Regression test: modify via `pyrite task update`, run sync, verify
      consistent with direct-write path
- [ ] The documentation or sync output explicitly signals when files are
      detected as unchanged vs. skipped due to a sync-tracking error

## Workarounds (until fixed)

- Prefer `pyrite task update` over direct frontmatter edits for task files
- For bulk workflows involving worker agents that edit KB files, follow
  with `pyrite index build --kb <kb>` instead of `pyrite index sync`
- Conductor ticks that absorb worker output should sanity-check by reading
  the file directly (Grep / Read) rather than trusting `task list` output

## Related

- `pyrite/kb/backlog/add-blocked-on-optional-field-to-task-schema.md` —
  the `dependencies` field already works end-to-end via the sanctioned CLI
  path, but was silent on direct-edit path until this bug is fixed
- `pyrite/kb/backlog/canonicalize-capture-lanes-taxonomy-cascade-timeline.md` —
  the proposed migration script will rely on incremental sync to detect
  which files it touched; blocks on this bug
