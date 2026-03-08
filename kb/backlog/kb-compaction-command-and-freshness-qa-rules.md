---
id: kb-compaction-command-and-freshness-qa-rules
type: backlog_item
title: "KB Compaction Command and Freshness QA Rules"
kind: feature
status: completed
priority: 11
effort: S
milestone: "0.17"
tags: [qa, cli, compaction, staleness]
---

# KB Compaction Command and Freshness QA Rules

## Summary

Type-aware staleness detection and archival candidate identification for knowledge bases.

## What Was Implemented

### QA Service Extensions (`qa_service.py`)

- **`find_stale(kb_name, max_age_days)`**: Finds active entries not updated within N days. Type-aware: historical types (adr, event, timeline, qa_assessment, relationship) are exempt.
- **`find_archival_candidates(kb_name, min_age_days)`**: Finds completed backlog items and old orphan entries (no links, low importance) that could be archived.
- **`validate_kb()` staleness integration**: Optional `check_staleness` and `staleness_days` parameters add `stale_entry` info-level issues to validation results.

### CLI Commands

- **`pyrite qa stale <kb> [--max-age N]`**: Reports stale entries with rich table output or JSON/CSV/YAML.
- **`pyrite qa compact <kb> [--min-age N]`**: Reports archival candidates (dry-run only — no entries modified). Suggests `pyrite update <id> --lifecycle archived` for follow-up.

### Staleness Exempt Types

Types that are historical by design are never flagged as stale:
- `adr` — architecture decisions are historical records
- `event` — past occurrences don't go stale
- `timeline` — chronological records
- `qa_assessment` — point-in-time snapshots
- `relationship` — structural links don't age
