---
id: rubric-checkers
type: component
title: "Rubric Checkers"
kind: module
path: "pyrite/services/rubric_checkers.py"
owner: "markr"
dependencies: ["pyrite.services.qa_service", "pyrite.schema.core_types"]
tags: [core, qa, validation, rubric]
links:
  - target: qa-service
    relation: part_of
    note: "Rubric checkers are used by QAService for evaluation"
---

Named registry of deterministic rubric checker functions. Each checker validates one rubric item against an entry and returns an issue dict or None. Checkers are looked up by name via the `NAMED_CHECKERS` registry.

## Architecture

- `NAMED_CHECKERS`: dict mapping checker names to callable functions — the sole lookup mechanism
- `GENERIC_TITLES` — frozenset of title strings considered too vague (e.g., "Update", "Notes", "TODO")
- `_parse_metadata(entry)` — extracts metadata dict from entry (handles JSON string or dict)

## Checker Functions

All checkers accept `(entry, schema, params=None)` and return an issue dict or None.

- **Structural**: `check_descriptive_title`, `check_has_tags`, `check_has_outlinks`, `check_status_present`, `check_priority_present`
- **Parameterized field**: `check_has_field` (params: `{field}`), `check_has_any_field` (params: `{fields}`)
- **Body structure**: `check_body_has_section` (params: `{heading}`), `check_body_has_pattern` (params: `{pattern}`), `check_body_has_code_block`

## Integration

Called by `QAService._check_rubric_evaluation()` via named lookup. Rubric items in `kb.yaml` bind to checkers using `{text, checker, params}` dict format. Plain string items are judgment-only (LLM-evaluated). Items with `covered_by: schema` are skipped.

Plugins register additional checkers via `PyritePlugin.get_rubric_checkers()`, aggregated by `PluginRegistry.get_all_rubric_checkers()`.
