---
id: schema-versioning
title: "Schema Versioning and Migration"
type: backlog_item
tags:
- feature
- schema
- migration
- core
kind: feature
priority: high
effort: M
status: planned
links:
- intent-layer-guidelines-and-goals
- pyrite-ci-command
- roadmap
---

## Problem

Schemas evolve. You add a required field to a type, tighten a controlled vocabulary, or rename a field — and now hundreds of existing entries are technically invalid. `pyrite ci` will fail on entries that were fine yesterday. There's no migration story: no way to add defaults to existing entries, no way to distinguish "required for new entries" vs "required for all entries," and no way to track which schema version an entry was created under.

This matters especially for corporate teams and long-lived KBs where schema changes are inevitable.

## Solution

### Schema Version Tracking

Add a `version` field to kb.yaml:

```yaml
name: my-kb
version: 3  # increments on schema changes
types:
  finding:
    fields:
      confidence:
        type: number
        required: true
        since_version: 3  # only required for entries created at v3+
```

Entries get a `_schema_version` in their metadata (or frontmatter) at creation time.

### Migration Commands

```bash
# Show what would change
pyrite schema diff --from 2 --to 3

# Dry-run migration
pyrite schema migrate --kb research --dry-run

# Apply migration (adds defaults, updates controlled vocab)
pyrite schema migrate --kb research

# Validate at specific version
pyrite ci --schema-version 2  # lenient mode for legacy entries
```

### Migration Strategies

- **Add default**: New required field gets a default value applied to existing entries
- **Backfill**: New required field gets computed from existing data (e.g., `confidence` derived from source count)
- **Soft require**: Field required for new entries, warning-only for legacy (`since_version`)
- **Rename**: Old field name maps to new name during migration
- **Vocabulary expansion**: New allowed values added — no migration needed
- **Vocabulary restriction**: Old values mapped to new values via migration table

### QA Integration

`pyrite ci` and QA validation should be schema-version-aware:
- Entries created before a requirement was added get warnings, not errors
- Migration status surfaced in `pyrite qa status`
- "Unmigrated entries" as a QA metric

## Prerequisites

- Schema-as-config (done)
- Intent layer phase 1 (guidelines in kb.yaml) — ships together naturally

## Success Criteria

- kb.yaml supports `version` field
- Entries track their creation schema version
- `pyrite schema migrate` applies defaults and renames
- `pyrite ci` distinguishes legacy entries from new violations
- Migration is idempotent and safe (dry-run first)

## Launch Context

Must ship before 0.8. Without this, the first schema change after launch breaks every existing KB. The `since_version` pattern is the minimum — it lets schemas evolve without invalidating existing content.
