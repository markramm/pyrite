---
id: bug-mcp-kb-create-places-entries-at-kb-root-instead-of-type-directory
title: "Bug: kb_create MCP tool places entries at KB root instead of type directory"
type: backlog_item
tags:
- bug
- mcp
- agents
kind: bug
status: proposed
priority: high
effort: s
milestone: "0.13"
links:
- clarify-metadata-vs-top-level-field-mapping-in-mcp-create-update-tools
- bug-kb-update-mcp-tool-returns-posixpath-serialization-error
---

## Problem

When creating entries via the `kb_create` MCP tool, files are placed at the KB root directory instead of the appropriate subdirectory for their type. For example, `backlog_item` entries should go in `kb/backlog/` but instead land in `kb/`.

Observed with 8 entries created via MCP — all landed at root:
- `kb/agent-oriented-error-responses-across-cli-and-mcp.md`
- `kb/bug-kb-update-mcp-tool-returns-posixpath-serialization-error.md`
- `kb/clarify-metadata-vs-top-level-field-mapping-in-mcp-create-update-tools.md`
- `kb/knowledgeclaw-pyrite-powered-agent-for-openclaw-ecosystem.md`
- `kb/mcp-search-add-fields-parameter-for-token-efficient-results.md`
- `kb/mcp-tool-kb-batch-read-for-multi-entry-retrieval-in-one-call.md`
- `kb/mcp-tool-kb-list-entries-for-lightweight-kb-index-browsing.md`
- `kb/mcp-tool-kb-recent-for-what-changed-orientation-queries.md`

All have `type: backlog_item` and should have been placed in `kb/backlog/`.

## Expected Behavior

`kb_create` should respect the KB's directory conventions. If the KB has a directory structure that maps types to subdirectories (e.g., `backlog_item` → `backlog/`, `adr` → `adrs/`, `component` → `components/`), new entries should be placed accordingly.

## Likely Cause

The MCP tool handler for `kb_create` probably builds the file path from just `kb_root / f"{entry_id}.md"` without consulting the type-to-directory mapping. The CLI `pyrite create` command may have the same issue or may handle it differently.

## Fix

Check how the storage layer resolves file paths for new entries. The type → directory mapping likely exists somewhere (kb.yaml type definitions, or convention-based) but isn't being consulted during MCP create.
