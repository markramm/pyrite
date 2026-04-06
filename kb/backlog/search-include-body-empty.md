---
id: search-include-body-empty
type: backlog_item
title: "Search --include-body returns empty body field in JSON results"
kind: bug
status: proposed
priority: high
effort: M
tags: [cli, search, bug]
---

## Problem

When running `pyrite search --include-body --format json`, the `body` field in results is empty despite entries having content. This breaks programmatic workflows that search and then process entry content (e.g., agent-driven curation, export pipelines).

## Expected Behavior

`--include-body` should populate the `body` field with the entry's markdown content. If the body is large, it should be truncated with a `body_truncated: true` flag rather than returned empty.

## Reproduction

```bash
pyrite search "some query" --include-body --format json
# body field is empty string in results
```

## Acceptance Criteria

- `--include-body` returns actual body content in JSON results
- Large bodies are truncated with metadata indicating truncation
- Body content matches what `pyrite get <id>` returns
