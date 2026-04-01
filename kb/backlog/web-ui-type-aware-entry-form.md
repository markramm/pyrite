---
id: web-ui-type-aware-entry-form
type: backlog_item
title: "Web UI: type-aware entry creation form with dynamic fields"
kind: bug
status: todo
priority: critical
effort: L
tags: [web, ux, entry-creation, schema]
---

## Problem

The web UI "New Entry" form only shows generic fields (title, body, tags, date, importance, status) regardless of entry type. When a user creates an "asset" entry in a journalism-investigation KB, they should see fields for `asset_type`, `jurisdiction`, `value`, etc. Instead they get a blank body and no type-specific guidance.

This works correctly on CLI (`-f` flag), MCP (structured params), and API (JSON body) — only the web UI is missing type awareness.

## Solution

1. **API: type schema endpoint** — `GET /api/kbs/{kb}/types/{type}/schema` returns the field definitions (name, type, required/optional, description) for a given entry type in a given KB. Sources: kb.yaml type schema fields, core type dataclass fields, plugin type fields.

2. **API: entry types with metadata** — Enhance `GET /api/entries/types?kb=` to return type descriptions and field counts, not just type name strings.

3. **Frontend: dynamic form fields** — The new entry page renders type-specific fields based on the schema response. Field types map to input widgets (text, date, number, select, list, object-ref).

4. **Frontend: type selector** — When creating a new entry, show available types for the KB with descriptions, not just a text input defaulting to "note".

## Reported By

User testing journalism-investigation plugin (2026-03-31). Entities created via web UI had blank bodies and only default fields.
