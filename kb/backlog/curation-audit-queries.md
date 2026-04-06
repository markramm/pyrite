---
id: curation-audit-queries
type: backlog_item
title: "Add curation coverage queries: sourcing rates, link density, KB health dashboard"
kind: feature
status: proposed
priority: high
effort: M
tags: [curation, search, cli, mcp]
---

## Problem

`pyrite qa validate` catches structural *issues* (broken links, missing fields, orphans, etc.) but there's no way to get a *coverage overview* of a KB's curation state. You can't easily answer:

- "What percentage of this KB's entries are sourced?"
- "What's the average link density per entry type?"
- "How many entries are still at stub/draft status vs working/complete?"
- "Which high-importance entries have thin bodies?"
- "What's the sourcing rate for entries above stub status?"

These are different from QA issues — they're aggregate health metrics for planning curation work, not per-entry validation failures.

## Non-Overlap with QA Validate

QA validate already handles: orphan detection, broken links, empty bodies, missing titles, schema violations, rubric checks. This item does NOT duplicate those. It adds:

1. **Coverage stats** — aggregate percentages and distributions, not issue lists
2. **Sourcing awareness** — including inline document references (EFTA IDs, court filing numbers), not just structured `sources:` field. KB-configurable source detection patterns.
3. **Status distribution** — entries by research_status, showing curation pipeline throughput
4. **Comparative metrics** — "this KB is 47% sourced vs cascade-timeline at 99%"

## Expected Behavior

Extend `pyrite qa` or `pyrite kb stats` with coverage subcommands:

```bash
pyrite qa coverage cascade-research          # full coverage report
pyrite qa coverage cascade-research --type actor  # per-type breakdown
pyrite qa coverage --all                     # compare across KBs
```

Output example:
```
cascade-research coverage:
  Entries: 378 (34% complete, 25% stub, 14% draft, 14% working)
  Sourced: 47.8% (structured) + 31.2% (inline refs) = 79.0% effective
  Linked: 76.9% have outbound wikilinks, avg 3.2 per entry
  Thin entries: 18 entries with importance > 5 and body < 200 words
```

Also expose via MCP (read tier) for agent-driven curation planning.

## Design Notes

- Source detection should be configurable per KB in kb.yaml — e.g., `source_patterns: ["EFTA\\d+", "Case No\\."]` for inline reference detection
- Coverage stats are simple SQL aggregations against the existing index
- Consider caching stats with a TTL since they're expensive on large KBs

## Acceptance Criteria

- `pyrite qa coverage` command with per-KB and cross-KB views
- Status distribution, sourcing rate (structured + inline), link density
- Per-type breakdown option
- MCP tool for agent-driven curation planning
- KB-configurable inline source reference patterns
