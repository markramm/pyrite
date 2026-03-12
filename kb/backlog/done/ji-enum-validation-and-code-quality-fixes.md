---
id: ji-enum-validation-and-code-quality-fixes
title: 'JI: Enum validation and code quality fixes'
type: backlog_item
tags:
- ji
- quality
- refactor
kind: tech_debt
status: done
assignee: claude
effort: S
---

## Problem

Code review identified several quality issues in the journalism-investigation plugin:

1. **Missing enum validation**: The validator checks claim_status and confidence against constants but does not validate asset_type, account_type, evidence_type, transaction_type, case_type, case_status, mechanism, or reliability against their defined enum tuples. The constants are defined but unused.

2. **Duplicated code**: JSON metadata parsing (5-line block repeated 7 times in MCP handlers), EventStatus parsing (repeated 3 times in from_frontmatter methods), import json repeated per-handler instead of module-level.

3. **str(None) safety**: Multiple from_frontmatter methods use str(meta.get("field", "")) which produces "None" instead of "" when YAML has explicit null values.

4. **summary field inconsistency**: Entity types conditionally add summary in to_frontmatter(), event types do not. Should be consistent.

## Scope

### Enum Validation (TDD)
- Add validation for all enum fields in _validate_investigation_entry
- Validation should warn on invalid values, not block (enums are advisory, new values may be valid)
- Add tests for invalid enum values across all entry types

### Code Dedup
- Extract _parse_meta(entry_dict) helper for JSON metadata parsing
- Extract _parse_event_status(meta) helper for EventStatus parsing
- Move import json to module level in plugin.py

### Safety Fixes
- Add _str_or_empty(value) helper that returns "" for None
- Apply consistently across all from_frontmatter methods

## Acceptance Criteria

- All enum fields validated with warnings for invalid values
- No duplicated 5-line metadata parsing blocks
- str(None) returns "" not "None" in all from_frontmatter methods
- All existing tests still pass
- New tests for enum validation edge cases
