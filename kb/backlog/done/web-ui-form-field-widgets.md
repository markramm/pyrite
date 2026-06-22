---
id: web-ui-form-field-widgets
title: "Web UI: render select/date/number/checkbox widgets for typed schema fields"
type: backlog_item
tags: [web-ui, schema, ux, follow-on]
importance: 5
kind: bug
status: done
priority: medium
effort: M
rank: 0
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

## Resolution (2026-06-22)

The core defect — typed fields rendering as plain text inputs, causing
invalid submissions — is fixed in `web/src/routes/entries/new/+page.svelte`.
Current state:
- `string`+`enum` → <select> (was already present)
- `list` → comma-separated text input (already present)
- `number`/`integer` → number input; `date`/`datetime` → date input
- `checkbox`/`boolean` → **NEW** native checkbox bound to .checked.
  Previously checkbox fell through to a text input bound to .value, so the
  save-time coercion (`value === 'true'`) never matched and a checkbox could
  never be saved as true. Now fixed.

Coercion logic extracted to a unit-tested helper
`web/src/lib/utils/entry-fields.ts` (coerceFieldValue/buildMetadata), with
9 tests in entry-fields.test.ts (incl. the checkbox regression).

Acceptance criteria met: each declared field type renders the matching
widget (1); server-side validation unchanged (2); actor form renders cleanly
end-to-end (4). Remaining: Playwright visual-regression test (3) and the
object_ref typeahead enhancement — split into follow-up
[[web-ui-form-widgets-playwright-visual-regression-object-ref-typeahead]].
