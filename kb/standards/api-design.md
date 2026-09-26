---
id: api-design
title: "API & MCP Tool Design"
type: standard
tags: [api, mcp]
importance: 5
category: api
---

## MCP Tool Naming
- Plugin tools prefixed with short name: `sw_`, `zettel_`, `wiki_`
- Read tools: list/query operations
- Write tools: create/update operations
- Admin tools: management operations

## Tool Schema
Every MCP tool must have:
- `description` — clear, actionable description
- `inputSchema` — JSON Schema with type, properties, required
- `handler` — method reference on the plugin class

## Error Handling

ADR-0037 theme 2 (maintainer decision, 2026-09-25): **codes live on the
exception class.** Every `PyriteError` subclass (`pyrite/exceptions.py`)
carries a class-level `error_code` and a safe `public_message` (`None` when
`str(exc)` itself is already safe to show). Every surface derives its code
from the class the same way — no per-transport lookup table keyed by
exception type — but each surface keeps its own wire shape:

**CLI (`--format json`) and MCP tool responses** return the same flat shape:

```json
{
  "error": "human-readable message",
  "error_code": "MACHINE_CODE",
  "suggestion": "optional fix hint",
  "retryable": false
}
```

- `error` and `error_code` and `retryable` are always present.
- `suggestion` is omitted entirely when there's no applicable fix hint
  — don't assume the key exists.
- Match on `error_code`, not on `error` text, which is for humans and
  can change wording.
- `retryable: true` means the same request could succeed on retry
  (e.g. a transient lock); `false` means the request itself needs to
  change (e.g. a malformed query).
- **MCP only, for one release:** where REST's code differs from what MCP
  used to report for a class, the tool response also carries the old code
  in `legacy_error_code`. The CLI has no such field.

**REST** answers `{"detail": {"code", "message", "retryable", "hint"?}}` —
the single shape every REST path uses, whether the refusal reached the
central `PyriteError` handler (`server/errors.py`) or an endpoint's own
`HTTPException(detail={...})`.

Build errors via the shared helper (`pyrite/utils/errors.py`'s
`build_error`/`cli_error`/`cli_error_from` for CLI, MCP's `_error()`/
`_refusal()` in `server/mcp_server.py`, or REST's `server/errors.py`) —
never hand-roll `{"error": "message"}`. The full canonical contract
(including success envelopes, body-truncation fields, and exit codes) is
documented in `docs/json-contracts.md`.

Return guidance for file creation (create tools don't write files
directly, they return instructions).

## Provenance

The error-shape convention above was landed and swept CLI-wide in
[[cli-error-shape-consistency]] (done) — see that ticket for the
mechanical conversion history. This standard, not the closed ticket,
is the canonical reference going forward.
