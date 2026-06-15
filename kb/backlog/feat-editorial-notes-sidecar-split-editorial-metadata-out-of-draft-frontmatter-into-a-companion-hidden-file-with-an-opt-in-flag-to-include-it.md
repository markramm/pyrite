---
id: feat-editorial-notes-sidecar-split-editorial-metadata-out-of-draft-frontmatter-into-a-companion-hidden-file-with-an-opt-in-flag-to-include-it
title: "feat: editorial-notes sidecar — split editorial metadata out of draft frontmatter into a companion file (opt-in flag to include it)"
type: backlog_item
tags: [feature, conductor-filed, indexing, drafts-kb, schema]
importance: 5
kind: feature
status: proposed
priority: high
effort: M
rank: 1450
---

FEATURE (Mark direction 2026-06-11, from the data-colonialism drafting session). PROBLEM: drafts in the drafts KB carry heavy editorial metadata in frontmatter — editorial_notes (nested mappings + multi-line block scalars), triage_log, fact-check verdicts, reviser logs. This (1) clogs the draft so search returns editorial cruft instead of the piece, (2) bloats the published-surface artifact, and (3) is the PRIMARY SOURCE of malformed-YAML index-sync failures (unquoted colons/em-dashes in verdict strings, bad block-scalar indent, duplicate keys) — ~27 drafts were unindexed because of it as of 2026-06-11.

PROPOSAL: separate editorial metadata from the draft into a COMPANION SIDECAR FILE per draft. The draft itself keeps only real content + minimal frontmatter (id/title/type/status/tags). The editorial apparatus is preserved (not deleted) but lives outside the searched/published surface.

## Design (LOCKED 2026-06-15 by Mark)

All 7 design defaults accepted. Rank set to r1450 (above r1400 since the conductor friction is active — 27 drafts unindexed). Kept separate from r1175 (different subsystems: drafts vs tasks).

### Sidecar file convention (decision #1)

`<entry-id>.editorial.md` next to `<entry-id>.md` in the same directory. Visible sibling, git-tracked. The indexer skips `*.editorial.md` via the same glob-pattern mechanism that already skips `_templates/`, README files, and hidden dirs (see `pyrite/storage/repository.py:list_files`).

Rationale: visible-by-default matches the "editorial apparatus is preserved, not deleted" framing. Easier to find, grep, and reason about than a hidden file. Adding the skip pattern is straightforward.

### Default `pyrite get` behavior (decision #2)

`pyrite get <entry-id>` does NOT include sidecar metadata by default. New `--with-editorial` opt-in flag merges the sidecar's mapping into the returned dict under a top-level `editorial:` key.

```bash
pyrite get my-draft -k drafts                   # clean piece, no editorial cruft
pyrite get my-draft -k drafts --with-editorial  # piece + editorial: {notes, triage_log, fact_check, ...}
```

Same flag pattern on `pyrite search` and (where relevant) `pyrite ls`.

### Search flag shape (decision #3)

Both flags ship in v1:

- `pyrite search <query> --with-editorial` — FTS body extended to include sidecar content; results may surface either the main entry or the sidecar but the entry-id and shape stay the same.
- `pyrite search <query> --editorial-only` — filters to entries that have a sidecar AND match in sidecar content. Used for editorial-workflow queries (e.g., "find all drafts where fact_check.verdict matches X").

Flags can be combined sensibly with all other search filters (`--type`, `--tag`, etc.).

### Sidecar schema (decision #4)

Hybrid: declared fields validated, unknown keys allowed but flagged at `pyrite kb validate`.

Per-type schema declared in the type's TypeSchema (alongside `state_machine` from r1175 / ADR-0027). Known fields for the drafts type: `editorial_notes`, `triage_log`, `fact_check`, `reviser_log` (each with its own sub-schema if useful). Unknown keys land in the parsed sidecar dict but get a warning at `kb validate` time.

Rationale: the 27-draft index-failure symptom IS the YAML grammar going wrong (unquoted colons, bad indents). A declared schema catches structural issues at write time; the freeform escape hatch keeps user flexibility for evolving editorial workflows.

### Migration helper (decision #5)

`pyrite drafts extract-editorial <kb> [--dry-run]` walks every entry in the KB, finds known editorial keys (from the type's sidecar schema) in the entry's frontmatter, and moves them to a new `<entry-id>.editorial.md` sidecar. Idempotent. Dry-run-safe per the r1175 migration pattern.

One direction only. The reverse (folding sidecar back into frontmatter for export) is filed as a follow-up if/when an export pipeline surfaces the need.

Lives in `pyrite/cli/drafts_commands.py` (creating the command group if it doesn't yet exist) or under the conductor's drafts plugin if one materializes by implementation time.

### Scope (decision #6)

**General primitive**, not drafts-KB-specific. Any KB can opt into sidecars via a `kb.yaml` flag:

```yaml
# kb.yaml
sidecars:
  enabled: true        # default false for back-compat; opt-in per KB
```

Per-type schema (decision #4) lives in TypeSchema; the KB-level flag controls whether the indexer treats `*.editorial.md` as sidecar (skipped by default) or as a regular entry (would happen if a KB has the flag off — unlikely but allowed for migration scenarios).

Rationale: drafts motivates the feature but any KB with editorial-style workflows (journalism-investigation review pipeline, social KB with talk-page workflows) benefits.

### Wikilink/backlink behavior (decision #7)

Editorial wikilinks NEVER contribute to the graph by default. The sidecar is invisible to the indexer, including its `[[...]]` references. The graph view shows only links from the main piece.

Future enhancement: a separate query path that builds an editorial-aware graph when explicitly requested (`pyrite graph <entry-id> --with-editorial`). Not v1.

Rationale: if editorial is invisible by default, its outlinks should be too — otherwise the graph shows links that don't correspond to anything findable in normal search. Confusing inconsistency.

## Acceptance criteria

- KB-level `sidecars.enabled` flag in `kb.yaml`; default False; opt-in per KB.
- Type-level sidecar schema declaration alongside existing TypeSchema fields. Known fields validated; unknown keys land in parsed sidecar dict + `kb validate` flags them.
- Indexer skips `*.editorial.md` files when the KB has sidecars enabled.
- `pyrite get <id>` excludes sidecar by default; `--with-editorial` merges it under `editorial:` key in the returned dict.
- `pyrite search <q> --with-editorial` extends FTS to sidecar content.
- `pyrite search <q> --editorial-only` filters to sidecar-having entries matching in sidecar content.
- `pyrite drafts extract-editorial <kb> [--dry-run]` migrates known editorial frontmatter keys to sidecar files. Idempotent.
- Wikilinks inside sidecars do NOT contribute to the graph by default.
- Regression test: a draft with editorial frontmatter that previously failed `pyrite index sync` (one of the 27 known failure cases, if reproducible) succeeds after migration.

## Implementation arc

Estimated ~5 fires:

1. RED tests for sidecar reader/writer + indexer skip + per-KB flag plumbing
2. GREEN: sidecar reader/writer + `kb.yaml` flag + indexer skip pattern
3. `--with-editorial` flag on `pyrite get` + `pyrite search` + the `--editorial-only` filter
4. Migration script `pyrite drafts extract-editorial <kb>` + tests
5. ADR (probably ADR-0029) + close ticket

M effort.

## Related

- ADR-0027 (per-entity-type state machine config) — same Reading C precedent: per-type config lives on TypeSchema
- `bug-from-markdown-splits-on-body-triple-dash-parsing-prose-as-frontmatter-yaml` (closed in r1030) — adjacent symptom of editorial-metadata-in-frontmatter; relaxing the parser helped one symptom, sidecars fix the root cause
- Conductor friction: the data-colonialism drafting session 2026-06-11 surfaced this; subsequent session on 2026-06-15 confirmed it's recurring ("we keep having issues with that frontmatter")
- Future: editorial-aware graph view as a follow-up enhancement to wikilink behavior

## PO note

Rank set to r1450 — above r1400 (split-backend-protocol, design-locked at 3777cb5) since the conductor friction is active and a 27-draft unindexed cluster is a concrete symptom. r1400's 8-fire arc is in flight (fire 1 at 607e916); the loop will work whichever is highest-priority and unblocked.
