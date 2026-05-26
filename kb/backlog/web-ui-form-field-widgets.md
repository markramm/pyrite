---
id: web-ui-form-field-widgets
type: backlog_item
title: "Web UI: render select/date/number/checkbox widgets for typed schema fields"
kind: bug
status: proposed
priority: medium
effort: M
tags: [web-ui, schema, ux, follow-on]
---

## Problem

The `web-ui-type-aware-entry-form` ticket (done) added a type-schema endpoint
and a dynamic form, but it renders every field as a plain text input.

Today: a field declared `status: select` with enum
`[draft, published, archived]` shows a free-text box. A `date` field shows
a free-text box. A `boolean` field shows a free-text box. A numeric range
field with min/max shows a free-text box.

Result: users (and especially agents) submit invalid values. Validation
fires on save, error round-trips to the UI, and the only escape is to look
at `kb.yaml` or run `pyrite schema` to figure out what to type. The original
ticket's acceptance criterion 3 — "Field types map to input widgets (text,
date, number, select, list, object-ref)" — is partially unmet.

## Solution

In `web/src/lib/components/entry-form/`:

1. Read the field's `type` and `constraints` from the schema response.
2. Render the appropriate widget:
   - `string` + `enum: [...]` → `<select>` populated from enum
   - `string` + `pattern` → text input with regex hint
   - `date` → date picker
   - `number` / `integer` → number input with min/max bounds
   - `boolean` → checkbox
   - `list[string]` → tag-input pill widget
   - `object_ref` → typeahead against existing entries of the referenced
     type
3. Expose the constraints on the schema endpoint if they aren't already
   surfaced (companion ticket `schema-constraints-in-mcp-and-rest`).

## Acceptance criteria

- Each declared field type renders the matching widget.
- Server-side validation still fires; widget-level validation is best-effort.
- Visual regression test (Playwright) covering one of each widget type.
- The journalism-investigation `actor` form renders cleanly end-to-end (the
  failure mode that drove the original ticket).

## Related

- `web-ui-type-aware-entry-form` (done) — this fills the gap that ticket left
- `schema-constraints-in-mcp-and-rest` — surfaces the constraints needed
  here for both surfaces
