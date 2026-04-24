---
id: rename-move-support-with-redirect-and-wikilink-rewrite
type: backlog_item
title: "Rename/move support: rename a KB entry, leave redirect stub at old path, rewrite all internal [[wikilinks]]"
kind: feature
status: proposed
priority: high
effort: M
tags: [cli, wikilinks, refactor, external-links, kb-hygiene]
---

## Problem

Pyrite currently has no first-class command for renaming or moving a KB entry. In practice this means:

- **Internal wikilinks break silently** when an entry is renamed. No grep-and-rewrite step is automated. The new name has to be manually hunted through every referencing file.
- **External links break** (capturecascade.org public pages, Substack articles citing KB slugs, other KBs cross-linking) with no redirect path.
- **Users avoid renaming even when the new name is clearly better**, because the cleanup cost is high enough that the KB accumulates slug-drift and misnomers. Examples from today's session (2026-04-23):
  - `task-inv5-ata-litigation-timeline` was superseded by the corrected UK-court understanding but the slug still contained "ATA" — had to close the task rather than rename
  - Worker AM surfaced a typo ("§ 2635.503" should be "§ 2635.502") that's structural enough that the slug it eventually spawned into a timeline entry could have propagated the error. Had the typo been in the entry ID, no rename path would exist.
  - Jurisdictional-correction task for Al-Khayyat/Doha Bank had to leave stale "ata-litigation" framing in one slug rather than rename

## Proposed command

```
pyrite entry rename <kb> <old-id> <new-id> [--redirect] [--update-links]
pyrite entry move <kb> <entry-id> <new-subdir>  # when the type/subdir should change
```

### Behavior

1. **Rename the file on disk** from `<old-id>.md` to `<new-id>.md`
2. **Rewrite the frontmatter `id:` field** to match the new id
3. **Rewrite all `[[<old-id>]]`, `[[<old-id>|alias]]` wikilinks across all KBs** in the pyrite index (not just the current KB — cross-KB wikilinks exist)
4. **With `--redirect`** (recommended default): leave a stub file at `<old-id>.md` containing:
   ```yaml
   ---
   id: <old-id>
   title: "Redirected: see [[<new-id>]]"
   type: redirect
   status: redirect
   redirect_to: <new-id>
   redirect_reason: "Renamed YYYY-MM-DD — <reason>"
   ---

   This entry has been renamed. See [[<new-id>]].
   ```
   The stub is indexed as a real entry so external links (e.g., capturecascade.org public pages, Substack citations) still resolve. The URL path still works; the content is a one-line pointer.
5. **Update the index**: old ID still searchable (resolves to the redirect); new ID resolves to the real entry.

### `--update-links` flag

Default behavior should be to rewrite wikilinks automatically (that's the point of the feature). `--update-links=false` for the rare case where someone wants to rename without mass-rewriting (e.g., intentionally preserving old references for historical study).

### `move` variant

When the subdirectory changes (e.g., a task moves from `notes/` to a different category, or an entry is reclassified from `actors/` to `organizations/`), `pyrite entry move` handles the subdir change in addition to the rename. KB-schema validation should re-run on the move target to ensure the entry-type matches the new subdir.

## Why priority high

1. **Unblocks a class of refactors the KB currently avoids**. Today's session had at least 3 cases where a rename was correct but the user/conductor chose to close+create rather than risk the wikilink breakage.
2. **The cost of renaming grows with KB size**. cascade-timeline has 4,888 entries; cascade-research has thousands across multiple subdirs. Manual grep-and-rewrite at that scale is not a real option.
3. **External-link preservation is a public-facing concern**. capturecascade.org published pages rely on KB slugs. Renaming without a redirect path breaks inbound links permanently.
4. **Enables KB hygiene tasks** (like the `canonicalize-capture-lanes-taxonomy-cascade-timeline` ticket) that would otherwise accumulate slug-drift over time.

## Acceptance criteria

- [ ] `pyrite entry rename <kb> <old-id> <new-id>` renames file, rewrites frontmatter id, rewrites all `[[<old-id>]]` wikilinks across every KB in the pyrite index
- [ ] `--redirect` flag (default true) leaves a redirect stub at the old path
- [ ] Redirect stub is indexed so external searches on the old ID resolve to a "renamed to X" pointer
- [ ] `pyrite entry move <kb> <entry-id> <new-subdir>` handles type/subdir changes with schema revalidation
- [ ] Dry-run mode (`--dry-run`) shows the proposed rename + link-rewrite plan without executing
- [ ] Regression test: rename an entry that is wikilinked from 5+ other entries across 2+ KBs; verify all links resolve to the new ID after rename
- [ ] Regression test: external URL to old slug continues to resolve via redirect stub (when a server is serving the KB content)

## Out of scope

- **Filesystem-level atomicity across multiple repos** (the rename may touch cascade-research, cascade-timeline, and other KBs simultaneously). If any step fails, require manual cleanup — a full transaction manager is overkill for this.
- **Fuzzy-match rewrite** of wikilinks that have drifted slightly from the canonical id. Only exact-match `[[<old-id>]]` rewrites. Fuzzy is a separate feature.
- **Git-commit integration** (e.g., auto-commit the rename as a single atomic git commit). Leave to user workflow.

## Workarounds currently in use

- Close the old task/entry with a "superseded by" note + create a new entry with the correct name
- Manually grep for `[[<old-id>]]` across KBs and fix each link by hand
- Avoid renaming altogether; live with slug drift

All three have observable costs (see 2026-04-23 session conductor log for three specific instances where rename-avoidance was chosen).

## Related

- `pyrite/kb/backlog/canonicalize-capture-lanes-taxonomy-cascade-timeline.md` — the canonicalization migration depends on rename support to execute cleanly
- `pyrite/kb/backlog/fix-incremental-sync-failing-to-reindex-modified-files.md` — separate pyrite defect; sync bug compounds rename pain because direct frontmatter edits don't propagate
- `pyrite/kb/backlog/add-blocked-on-optional-field-to-task-schema.md` — separate pyrite schema work
