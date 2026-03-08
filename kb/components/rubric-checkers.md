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

Pattern-matching registry of deterministic rubric checker functions. Each checker validates one rubric item (e.g., "Entry has a descriptive title") against an entry and returns an issue dict or None.

## Architecture

- `RUBRIC_CHECKERS`: list of `(re.Pattern, checker_fn)` tuples mapping rubric text to checker functions
- `match_rubric_item(item)` — looks up the checker for a rubric item string, returns None for judgment-only items
- `is_already_covered(item)` — returns True for rubric items already handled by existing QA rules (deduplication)
- `GENERIC_TITLES` — frozenset of title strings considered too vague (e.g., "Update", "Notes", "TODO")

## Checker Types

- **Direct checkers**: `check_descriptive_title`, `check_has_tags`, `check_has_outlinks`, `check_status_present`, `check_priority_present`
- **Factory functions**: `_make_metadata_field_checker`, `_make_metadata_any_field_checker`, `_make_body_section_checker`, `_make_body_has_code_block_checker`

## Integration

Called by `QAService._check_rubric_evaluation()` (single entry) and `QAService._check_rubric_all()` (bulk SQL path). Rubric items are sourced from `SYSTEM_INTENT`, `CORE_TYPE_METADATA`, and KB-level `kb.yaml` type schemas.
