---
id: migrate-all-rubric-items-to-named-checkers-and-remove-legacy-regex-path
title: Migrate All Rubric Items to Named Checkers and Remove Legacy Regex Path
type: backlog_item
tags:
- qa
- intent-engineering
- cleanup
links:
- target: epic-software-kb-quality-gates-and-rubric-automation
  relation: part_of
- target: named-rubric-checkers
  relation: depends_on
kind: feature
status: done
effort: M
---

## Problem

The named rubric checkers infrastructure is in place, but most rubric items across demo KBs (blank, boyd, wardley, kb-ideas) and the pyrite KB still use plain string format. These rely on the legacy regex matching path, which silently fails when phrasing doesn't match a hardcoded pattern (84% failure rate observed pre-named-checkers).

## Scope

1. **Migration tooling** — Add `pyrite qa migrate-rubric --kb <name>` command that:
   - Reads all rubric items (system, type, KB-level) for a KB
   - For each string item, suggests a named checker binding (auto-match where possible, prompt for manual binding)
   - Outputs the updated kb.yaml with named format items
   - Reports items that remain judgment-only

2. **Migrate demo KBs** — Convert blank, boyd, wardley, kb-ideas kb.yaml files to use named checkers where deterministic checkers exist. Mark schema-covered items with `covered_by: schema`.

3. **Migrate pyrite KB** — Convert the pyrite KB's own kb.yaml rubric items to named format.

4. **Migrate CORE_TYPE_METADATA** — Any remaining string-format items in type metadata for person, document, event, organization types (most already done).

5. **Remove legacy path** — Once all shipped KBs use named format:
   - Remove `RUBRIC_CHECKERS` regex list and `match_rubric_item()` function
   - Remove `_bind_params()` helper
   - Remove `ALREADY_COVERED_PATTERNS` and `is_already_covered()` (replaced by `covered_by: schema`)
   - Simplify `_check_rubric_evaluation()` to only handle dict items + plain string judgment-only

## Success Criteria

- All demo KBs and the pyrite KB use named-format rubric items
- `pyrite qa checkers --kb <name>` shows 0 regex-matched items
- Legacy regex matching code is removed
- No silent rubric failures
