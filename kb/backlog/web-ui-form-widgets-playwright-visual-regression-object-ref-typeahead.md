---
id: web-ui-form-widgets-playwright-visual-regression-object-ref-typeahead
title: 'Web UI form widgets: Playwright visual regression + object_ref typeahead'
type: backlog_item
tags:
- enhancement
- web
- frontend
- testing
importance: 5
status: proposed
priority: medium
rank: 0
---

Follow-up to web-ui-form-field-widgets (functional defect fixed 2026-06-22).

Remaining acceptance-criteria items not yet done:

1. **Playwright visual regression** covering one of each widget type
   (select / date / number / checkbox / list) on the new-entry form. Needs a
   seeded backend KB declaring a type with one field of each type. See
   web/e2e/entry-crud.spec.ts for the existing new-entry e2e patterns.

2. **object_ref typeahead**: fields of type `object_ref` should render a
   typeahead against existing entries of the referenced type, instead of a
   plain text input. Depends on the schema endpoint surfacing the referenced
   type (companion: schema-constraints-in-mcp-and-rest).

The functional widget rendering and the checkbox bug are already fixed; this
item is purely the test coverage + the object_ref enhancement.
