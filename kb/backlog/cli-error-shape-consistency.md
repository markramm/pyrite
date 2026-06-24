---
id: cli-error-shape-consistency
type: backlog_item
title: "Consistent CLI error shape: every error returns JSON with error_code + suggestion"
kind: improvement
status: proposed
priority: medium
effort: S
tags: [cli, ux, agent-ux, errors]
---

## Problem

Pyrite CLI error responses are not uniform.

- Entry not found returns structured JSON: `{"error": "...", "error_code":
  "NOT_FOUND"}`.
- KB not found returns rich text: `Error: KB not found: nonexistent-kb` —
  no error_code, no suggestion.
- `pyrite search` against an unregistered KB silently prints `No results
  found.` — looks like the query missed, not like the KB is wrong.

The MCP side has a clean `_error(code, message, suggestion, retryable)`
helper (`mcp_server.py:110`). The CLI doesn't, and the inconsistency is
visible to anyone driving Pyrite from a script or an agent.

## Solution

1. Promote the MCP `_error()` shape to a shared utility (e.g.,
   `pyrite/utils/errors.py`):
   ```python
   {
     "error": "human message",
     "error_code": "MACHINE_CODE",
     "suggestion": "optional fix hint",
     "retryable": false
   }
   ```
2. CLI commands print structured errors when `--format json` is set
   (already the case for many commands), and a colored single-line form
   otherwise:
   ```
   ERROR [NOT_FOUND]: Entry 'foo' not found in KB 'pyrite'.
       hint: try `pyrite search 'foo' -k pyrite` to find similar IDs
   ```
3. Replace ad-hoc `typer.echo(f"Error: ...")` / `raise typer.Exit(1)`
   sites with the new helper.
4. Bonus: detect the "unregistered KB" case in `search` and emit a
   distinct `KB_NOT_FOUND` error instead of a no-results return.

## Acceptance criteria

- All CLI errors emit `error_code` and (where useful) `suggestion`.
- JSON format matches the MCP error shape exactly.
- Unregistered-KB on search returns `KB_NOT_FOUND`, not empty results.
- Tests cover the four common error classes: NOT_FOUND, KB_NOT_FOUND,
  VALIDATION_FAILED, PERMISSION_DENIED.

## Related

- `agent-oriented-error-responses-across-cli-and-mcp` (done) — landed the
  MCP shape; this carries it to the CLI side
- `consistent-kb-flag-across-commands` — adjacent CLI consistency work

## Progress (2026-06-24)

Core landed (commit on this branch): shared `pyrite/utils/errors.py` with the
canonical shape; both `_cli_error` duplicates de-duplicated onto it; the
search-against-unregistered-KB bug fixed (now `KB_NOT_FOUND`, exit 1, lists known
KBs). Tests cover the helper shape + the KB_NOT_FOUND case.

**Remaining** (effort was under-estimated — this part is M, not S): convert the
~79 ad-hoc `typer.echo("Error: ...")` / `console.print("[red]Error...")` sites
across the CLI to the shared helper, and add tests for the full
NOT_FOUND/VALIDATION_FAILED/PERMISSION_DENIED set. The helper is in place; this is
a mechanical sweep.
