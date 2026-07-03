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

Every error surface — CLI (`--format json`), MCP tool responses, and
the REST `PyriteError` handler — returns the same canonical shape:

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

Build errors via the shared helper (`pyrite/utils/errors.py`'s
`build_error`/`cli_error`, or MCP's `_error()` in `mcp_server.py`) —
never hand-roll `{"error": "message"}`. That shape was the OLD
convention; the full canonical contract (including success envelopes,
body-truncation fields, and exit codes) is documented in
`docs/json-contracts.md`.

Return guidance for file creation (create tools don't write files
directly, they return instructions).

## Provenance

The error-shape convention above was landed and swept CLI-wide in
[[cli-error-shape-consistency]] (done) — see that ticket for the
mechanical conversion history. This standard, not the closed ticket,
is the canonical reference going forward.
