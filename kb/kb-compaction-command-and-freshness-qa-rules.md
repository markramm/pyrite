---
id: kb-compaction-command-and-freshness-qa-rules
title: KB Compaction Command and Freshness QA Rules
type: backlog_item
status: proposed
milestone: "0.17"
tags:
- enhancement
- qa
- search
metadata:
  kind: feature
  priority: medium
  effort: S
  status: proposed
kind: feature
priority: medium
effort: S
status: proposed
---

## Problem

Even with a lifecycle field ([[entry-lifecycle-field-and-search-filtering]]), identifying *which* entries to archive requires manual review. KBs with 200+ entries need automated detection of archival candidates. Additionally, different entry types age differently — component docs go stale, ADRs don't — but QA treats them uniformly.

## Solution

### 1. Compaction command

```bash
# Show archival candidates (dry run)
pyrite kb compact --kb pyrite --dry-run

# Archive candidates that match rules
pyrite kb compact --kb pyrite

# Custom thresholds
pyrite kb compact --kb pyrite --min-age 90 --min-importance 3
```

Detection rules for archival candidates:
- `backlog_item` with `status: done` and no inbound links from active entries
- `design_doc` where a linked ADR covers the same topic (detected via wikilinks)
- `note` with `importance <= 3` and no inbound links
- Any entry with 0 inbound links and last modified > configurable threshold (default 180 days)

Compaction suggests, human confirms. Sets `lifecycle: archived` — never deletes.

### 2. Type-aware freshness QA rules

Add `freshness_matters` flag to type metadata (in `CORE_TYPE_METADATA` or kb.yaml overrides):

| Type | Freshness matters | Rationale |
|------|-------------------|-----------|
| `component` | Yes | Should reflect current architecture |
| `design_doc` | Yes | Should be current or marked superseded |
| `standard` | Yes | Standards should be current |
| `adr` | No | Historical record by design |
| `backlog_item` | Partial | Active items yes, done items no |
| `note` | No | General-purpose, no currency expectation |

New Tier 1 QA rules (no LLM needed):
- **Staleness**: For `freshness_matters` types, warn if not updated in configurable window (default 90 days)
- **Superseded candidate**: Warn if a design doc's outbound wikilinks all point to ADRs
- **Orphan detection**: Flag entries with zero inbound links and low importance as archival candidates
- **Done-but-referenced**: Warn if a `done` backlog item is still linked from active entries (the referencing entry may need updating)

### 3. Configuration

In `kb.yaml`:
```yaml
compaction:
  staleness_days: 90        # warn after N days without update
  orphan_min_age_days: 180   # only flag orphans older than this
  orphan_max_importance: 3   # only flag orphans at or below this importance
```

## Prerequisites

- [[entry-lifecycle-field-and-search-filtering]] — lifecycle field must exist for compact to set it

## Success criteria

- `pyrite kb compact --dry-run` identifies reasonable archival candidates
- Staleness warnings appear for component docs not updated in 90+ days
- ADRs never get staleness warnings
- Orphan detection flags low-value unlinked entries
- All rules configurable via kb.yaml
- Rules integrate with existing QAService.validate_entry() path

## Files likely affected

- `pyrite/services/qa_service.py` — staleness, orphan, superseded-candidate rules
- `pyrite/services/kb_service.py` — compact operation
- `pyrite/schema.py` — freshness_matters in type metadata, compaction config in KBSchema
- `pyrite/cli/__init__.py` — `kb compact` command
- `pyrite/config.py` — compaction settings

## Related

- [[kb-compaction-and-entry-lifecycle]] — parent design
- [[entry-lifecycle-field-and-search-filtering]] — Phase 1 prerequisite
- [[qa-agent-workflows]] — freshness rules extend Tier 1 validation
- [[intent-layer]] — freshness signals complement intent evaluation rubrics
