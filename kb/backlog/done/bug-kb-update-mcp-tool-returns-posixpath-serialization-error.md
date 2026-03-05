---
id: bug-kb-update-mcp-tool-returns-posixpath-serialization-error
title: 'Bug: kb_update MCP tool returns PosixPath serialization error'
type: backlog_item
tags:
- bug
- mcp
- agents
metadata:
  kind: bug
  status: completed
  priority: high
  effort: s
kind: bug
status: done
priority: high
effort: s
milestone: "0.13"
---

## Problem

The `kb_update` MCP tool fails with `cannot represent an object: PosixPath('/Users/markr/pyrite/kb/...')` when returning a response after a successful or attempted update. The error is in the response serialization — the tool is trying to return a `PosixPath` object instead of converting it to a string.

## Reproduction

Call `kb_update` via any MCP client (Claude Desktop, Cowork, etc.) with valid parameters:

```
kb_update(
  entry_id="any-entry",
  kb_name="pyrite",
  title="Updated Title",
  body="Updated body content"
)
```

Returns error: `cannot represent an object: PosixPath('...')`

The update may or may not have been written to disk — the error occurs during response serialization, so it's unclear whether the write succeeded. In testing, the writes did NOT take effect.

## Fix

Likely a `str()` conversion missing on a `file_path` field in the update response dict. Check the MCP tool handler for `kb_update` — probably returning the raw `Path` object from the storage layer instead of casting to string.

## Impact

Blocks all MCP-based entry updates. Agents fall back to direct file editing (which bypasses schema validation and index sync). This is the kind of bug that silently degrades the agent experience — the agent gets an error, retries, gets the same error, and either gives up or works around it.
