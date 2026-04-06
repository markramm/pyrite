---
id: search-fallback-error-obscured
type: backlog_item
title: "Search silently falls back to file search when index search fails"
kind: bug
status: proposed
priority: medium
effort: S
tags: [cli, search, error-handling]
---

## Problem

In `cli/search_commands.py` (~line 139-146), when index-based search throws any exception, the CLI catches it, prints a brief error, and silently falls back to file search:

```python
except Exception as e:
    console.print(f"[red]Search error:[/red] {e}")
    console.print("[dim]Falling back to file search...[/dim]")
    _search_files(config, query, kb_name, entry_type, limit)
```

Problems:
1. The original error is lost — users don't know if the index is corrupt, the query syntax is bad, or the DB is locked
2. File search results may be much worse than index search, but users don't realize they're getting degraded results
3. In JSON output mode, you get an error JSON line followed by file search results — confusing for programmatic consumers

## Expected Behavior

- Clearly distinguish "index unavailable, using file search" from "query error, fix your query"
- In JSON mode, return a structured error response, don't mix error + fallback results
- Log the full exception at DEBUG level for troubleshooting
- Consider a `--no-fallback` flag for when you want the error, not degraded results

## Acceptance Criteria

- Index errors show the specific error type (corrupt, locked, query syntax)
- JSON mode returns clean error OR clean results, never both
- File search fallback is clearly labeled in output
