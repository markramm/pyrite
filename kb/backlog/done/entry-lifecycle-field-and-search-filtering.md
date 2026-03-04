---
id: entry-lifecycle-field-and-search-filtering
title: Entry Lifecycle Field and Search Filtering
type: backlog_item
tags:
- enhancement
- qa
- search
metadata:
  kind: feature
  priority: medium
  effort: S
  status: completed
kind: feature
priority: medium
effort: S
status: completed
---

## Problem

KBs only grow. Completed backlog items, superseded design sketches, and one-time notes rank alongside current component docs and active ADRs in search results. Agents get stale context mixed with current truth. There's no way to reduce the active search surface without deleting entries.

## Solution

Add an optional `lifecycle` field to entry frontmatter and filter non-active entries from default search.

### Lifecycle states

```yaml
lifecycle: active | archived | superseded
superseded_by: <entry-id>  # when lifecycle: superseded
```

- `active` (default, implicit if absent) — normal search ranking, full QA
- `archived` — excluded from default search, included with `--include-archived`. QA skips. Still in git, still queryable.
- `superseded` — like archived, but links to the replacement entry. Useful for design docs that became ADRs.

### Commands

```bash
# Archive an entry
pyrite kb archive <entry-id> --kb pyrite

# Mark as superseded
pyrite kb archive <entry-id> --superseded-by <replacement-id> --kb pyrite

# Search including archived
pyrite search "topic" --kb pyrite --include-archived
```

### Search and MCP integration

- CLI `pyrite search` excludes archived/superseded by default
- MCP `kb_search` adds `include_archived: bool` parameter (default false)
- REST API search endpoints add `include_archived` query param
- `pyrite get <id>` always works regardless of lifecycle (direct access is unfiltered)

### Entry model changes

- Add `lifecycle` field to `Entry` base class (optional, defaults to `active`)
- Add `superseded_by` field (optional, only valid when lifecycle is `superseded`)
- Index lifecycle in the search index for efficient filtering

## Prerequisites

None — this is additive to the existing entry model and search paths.

## Success criteria

- `lifecycle` field recognized in frontmatter, indexed, filterable
- Default search excludes archived/superseded entries
- `--include-archived` flag retrieves everything
- `pyrite kb archive` command sets lifecycle on entries
- Direct `pyrite get` access works regardless of lifecycle
- MCP tools support `include_archived` parameter

## Files likely affected

- `pyrite/models/base.py` — lifecycle field on Entry
- `pyrite/storage/index.py` — lifecycle-aware search filtering
- `pyrite/services/kb_service.py` — archive operation
- `pyrite/cli/__init__.py` — `kb archive` command, `--include-archived` on search
- `pyrite/server/mcp_server.py` — include_archived parameter on search tools
- `pyrite/server/endpoints/search.py` — include_archived query param

## Related

- [[kb-compaction-and-entry-lifecycle]] — parent design
- [[qa-agent-workflows]] — QA should skip archived entries
- [[intent-layer]] — lifecycle signals complement intent evaluation
