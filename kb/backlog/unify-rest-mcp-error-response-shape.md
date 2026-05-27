---
id: unify-rest-mcp-error-response-shape
type: backlog_item
title: "Unify error response shape across REST, MCP, and CLI"
kind: improvement
status: proposed
priority: medium
effort: M
tags: [rest-api, mcp, cli, errors, agent-ux, api-consistency]
---

## Problem

The same logical error is shaped three different ways depending on the
transport an agent/client uses:

- **REST (HTTPException)**: `{"detail": {"code": "...", "message": "..."}}` —
  the code/message nested under FastAPI's `detail` key.
- **REST (central PyriteError handler, added in `c348087`)**: top-level
  `{"code": "...", "message": "..."}` — NOT nested under `detail`.
- **MCP** (`mcp_server.py` `_error()` helper): `{"error": "...",
  "error_code": "...", "suggestion": "...", "retryable": ...}`.
- **CLI**: mix of structured `{"error","error_code"}` JSON and rich single-line
  text (see `cli-error-shape-consistency`).

So even within REST there are now two shapes (hand-rolled HTTPException details
vs. the central handler), and an agent that talks to both the REST API and the
MCP server has to parse two unrelated schemas. The audit (commit `c348087`)
introduced the central handler but deliberately did not retrofit every existing
`raise HTTPException(detail={...})` site, to keep that change reviewable.

## Solution

1. Pick one canonical error envelope (recommend the MCP shape, which already has
   `error_code` + `suggestion` + `retryable`):
   ```json
   {"error_code": "KB_NOT_FOUND", "message": "...", "suggestion": "...", "retryable": false}
   ```
2. Make the central REST handler emit that envelope (decide whether REST keeps
   the FastAPI `detail` wrapper or returns it top-level — pick one and document
   it in the OpenAPI schema).
3. Migrate the hand-rolled `raise HTTPException(status_code=..., detail={"code":
   ..., "message": ...})` sites (admin, worktree, templates, starred, search,
   entries, ai_ep, clipper) to either rely on the central handler or use a small
   shared helper that produces the canonical envelope.
4. Coordinate with `cli-error-shape-consistency` so the CLI emits the same
   envelope under `--format json`.

## Acceptance criteria

- One documented error envelope used by REST and MCP (and CLI JSON output).
- The central handler and remaining HTTPException sites produce identical shape
  and key names.
- A cross-transport test asserts the same `error_code` for the same condition
  (e.g. unknown KB) over REST and MCP.

## Related

- Commit `c348087` — added the central REST `PyriteError` handler (the source of
  the current two-REST-shapes situation this ticket resolves).
- `cli-error-shape-consistency` — the CLI half of the same unification.
- `mcp-rest-tool-parity`, `schema-constraints-in-mcp-and-rest` — adjacent
  REST/MCP parity tickets.
