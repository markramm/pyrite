---
id: cascade-timeline-static-export-for-viewer-consumption
title: Cascade timeline static export for viewer consumption
type: backlog_item
tags:
- cascade
- export
- api
- viewer
- static-site
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
assignee: claude
effort: M
---

## Reference Implementation

`/Users/markr/kleptocracy-timeline/timeline/scripts/generate.py` (~486 lines). A `TimelineGenerator` class that loads events from markdown, sorts by date, and produces multiple output formats. Read it for the exact field names and structures.

Also: `/Users/markr/kleptocracy-timeline/timeline/scripts/generate_csv.py` for CSV export format.

## Problem

The kleptocracy timeline project has a custom `generate.py` script that reads 4,400+ markdown event files and produces 4 static JSON files (timeline.json, actors.json, tags.json, stats.json) consumed by the React viewer and Hugo site. When the timeline KB is managed by Pyrite, this export step needs to be replicated as a Pyrite command so the existing viewer pipeline continues to work.

## Context

The current export pipeline produces:
- `timeline.json` (~19.5 MB) — full array of event objects with all metadata, sorted by date
- `actors.json` (~452 KB) — aggregated actor names with occurrence counts, sorted by frequency
- `tags.json` (~355 KB) — aggregated tags with counts
- `stats.json` (~1.7 KB) — summary statistics (total events, date range, top actors/tags, generation timestamp)

The React viewer at capturecascade.org loads these static files. The Hugo site reads markdown directly. Both are built in CI/CD and deployed to GitHub Pages.

### Output JSON Schemas

**timeline.json** — bare array of event objects sorted by date:
```json
[{"id": "...", "title": "...", "date": "2025-01-20", "actors": [...], "tags": [...], "sources": [{"title": "...", "url": "..."}], "body": "...", ...}]
```
Date fields are ISO strings. Events include all frontmatter fields plus body.

**actors.json** — array of `{name, count}` sorted by count descending:
```json
[{"name": "Donald Trump", "count": 1198}, {"name": "Elon Musk", "count": 487}, ...]
```

**tags.json** — array of `{name, count}` sorted by count descending:
```json
[{"name": "executive-power", "count": 892}, {"name": "judiciary", "count": 445}, ...]
```

**stats.json** — summary object:
```json
{"total_events": 4400, "total_tags": 150, "total_actors": 1235, "total_sources": 8800, "date_range": {"start": "1142-01-01", "end": "2026-03-09"}, "status_counts": {"verified": 2000, ...}, "top_tags": [...], "top_actors": [...], "generated": "2026-03-09T..."}
```

## Scope

- Create a `pyrite cascade export` CLI command that generates the 4 JSON files from KB entries
- Output format must be byte-compatible with the current `generate.py` output (same field names, same sort order, same structure)
- Support output directory specification: `--output-dir=path/to/api/`
- Support filtering: `--from=DATE --to=DATE`, `--tags=tag1,tag2`, `--min-importance=N`
- Generate CSV export as well (currently done by `generate_csv.py`)
- Optionally generate a diff report showing what changed since last export

## Acceptance Criteria

- `pyrite cascade export --kb=timeline --output-dir=./api/` produces timeline.json, actors.json, tags.json, stats.json
- Output is structurally identical to current `generate.py` output (React viewer works without changes)
- Export completes in under 60 seconds for 4,400+ events
- CSV export works: `pyrite cascade export --kb=timeline --format=csv`
- Incremental diff: `--diff` flag shows events added/modified/removed since last export
