---
id: index-rebuild-from-files-equivalence-test
title: Index rebuild from files equivalence test
type: backlog_item
tags:
- testing
- index
- storage
- ci
- programmatic-validation
- quality
links:
- target: mcp-tool-dispatch-smoke-test-every-registered-tool
  relation: related
  kb: pyrite
importance: 5
kind: improvement
status: proposed
priority: high
effort: M
rank: 0
---

## Problem

ADR-0001 and ADR-0029 state the founding principle: files in git are the
record, the database is disposable derived state. ADR-0029 also names the
consequence of violating it — "every recurrent field bug traces to derived
state diverging from its source of truth."

Nothing tests the principle. The recurrences so far:

- dual DB connections with non-atomic writes (ADR-0013);
- the dual KB registry, `config.yaml` vs the DB `kb` table (ADR-0029);
- `task update` / `pyrite update` leaving the index behind the file, read as
  data loss by two agents in one session (`FEEDBACK.md`, 2026-08-20,
  frictions 3 and 6; [[bug-pyrite-update-doesnt-keep-index-in-sync-with-source]]);
- a missing `type:` silently dropping `status:` from the indexed row
  (`FEEDBACK.md`, 2026-08-28);
- a KB registered over REST invisible until restart (PR #4 — the fourth
  occurrence of stale DB-registered KBs, after issues #1, #2 and 37a37c9).

Each was fixed at the symptom. None added a check that would catch the next
one.

## Proposed validation

An equivalence test, run in the default suite:

1. Seed a temp KB with a fixture corpus that covers every core type, at
   least one plugin type, links, tags, blocks, aliases, an edge-entity, and
   the known awkward cases (entry with no `type:`, unknown frontmatter
   keys, a `type:`-less entry carrying `status:`).
2. Drive it through the **incremental** paths a real session uses: create,
   update, rename, delete, `task claim`/`update`, `index sync` after direct
   file edits — via the service layer, not by writing rows.
3. Snapshot the index (entries, tags, links, blocks, FTS rows; normalized to
   drop timestamps and rowids).
4. Delete the DB. `pyrite index build` from files only.
5. Assert the rebuilt snapshot equals the incremental snapshot.

Any difference is, by definition, state that exists only in the DB or an
incremental path that disagrees with a clean parse — exactly the bug class.
Parametrize over backends so Postgres gets the same guarantee.

A second, smaller assertion: after every write-path call in step 2,
`get(id)` succeeds without an intervening `index sync`.

## Acceptance

- [ ] Test exists, runs in the default suite and CI, for SQLite; Postgres
      under the existing backend marker.
- [ ] Known current divergences are either fixed or listed as `xfail` with
      a linked ticket — not silently excluded from the fixture corpus.
- [ ] The normalizer's ignore-list (timestamps, rowids) is explicit and
      short; adding a column to it requires a comment saying why it is not
      derivable from files.
- [ ] Declared machinery tables (ADR-0029 §4 runtime state) are excluded by
      name, which doubles as the first enforced list of what "declared
      machinery" is.

## Notes

Filed from the 2026-09-17 whole-project review; one of five structural
checks (see [[mcp-tool-dispatch-smoke-test-every-registered-tool]] for the
set). Related: [[collapse-kb-registry-to-one-source-of-truth]],
[[core-types-silently-drop-unknown-frontmatter-keys]],
ADR-0001, ADR-0029.
