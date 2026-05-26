---
id: schema-constraints-in-mcp-and-rest
type: backlog_item
title: "Surface field constraints (min/max/enum/pattern) in kb_schema response"
kind: improvement
status: proposed
priority: medium
effort: S
tags: [mcp, api, schema, agent-ux]
---

## Problem

`kb_schema` (MCP) and the equivalent REST endpoint return field names and
types but not their constraints. Agents creating entries have no way to
discover that `importance` is 1..10, that `status` is one of a fixed enum,
or that an ID must match a slug pattern.

The result is trial-and-error: an agent attempts a value, the server
returns a validation error, the agent adjusts. This is wasteful tokens and
ugly UX.

The web UI faces the same problem (see `web-ui-form-field-widgets`).

## Solution

1. Extend the field schema serialization in `pyrite/schema/` to include:
   - `enum: [...]` when present in `FieldSchema`
   - `min`, `max` for numeric fields
   - `pattern` (regex) for string fields with a pattern constraint
   - `format` (date, datetime, url, email) when known
   - `description` (already present, but verify)
2. Reflect those keys in the MCP `kb_schema` tool response and the REST
   `/api/kbs/{kb}/types/{type}/schema` response. Same payload shape on both
   surfaces.
3. Tool description: update `kb_schema` so agents know constraints are
   present and how to use them.

## Acceptance criteria

- `kb_schema` returns constraints on every field that has them.
- REST endpoint returns the same shape.
- Existing schemas in `extensions/*/kb-templates/` carry constraints where
  they should (audit pass — e.g., `actor_tier`, `status`, `priority`).
- Tests assert constraint fields are present in the response.

## Related

- `web-ui-form-field-widgets` — UI consumer of the new constraint data
- ADR-0008 (structured data schema) — original constraints lived here but
  weren't surfaced on the API
