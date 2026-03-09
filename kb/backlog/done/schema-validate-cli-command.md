---
id: schema-validate-cli-command
type: backlog_item
title: "Schema validate CLI command and pre-commit hook"
kind: feature
status: done
milestone: "0.17"
priority: high
effort: M
tags: [cli, validation, pre-commit, data-integrity]
---

# Schema validate CLI command and pre-commit hook

## Problem

Invalid or inconsistent KB entries flow into the index silently. Three recent bugs — ID collisions, empty ADR dates, priority type mismatches — all stem from the same root: no validation gate between authoring and indexing. Errors are only discovered when data goes missing or displays incorrectly.

## Proposed solution

A `pyrite schema validate` command that checks markdown files against KB schema, DB constraints, and index state. Usable both interactively and as a pre-commit hook.

### Usage

```bash
# Validate specific files
pyrite schema validate kb/adrs/0017-entry-protocol-mixins.md

# Validate all files in a directory
pyrite schema validate kb/adrs/

# Validate all changed files (pre-commit integration)
pyrite schema validate --changed

# Validate entire KB
pyrite schema validate -k pyrite
```

### Checks to implement

1. **Frontmatter parse** — valid YAML, required `type` and `title` fields present
2. **Type schema conformance** — fields match `kb.yaml` type schema (field types, required fields, allowed values)
3. **Protocol field types** — values match DB column expectations (e.g., priority: integer vs string)
4. **ID collision detection** — generated slug doesn't collide with existing entry of different type
5. **Required fields per type** — ADRs need `adr_number`, `date`, `status`; backlog items need `kind`, `status`, `priority`
6. **Roundtrip integrity** — fields that get promoted to DB columns won't vanish through the write→read path
7. **Link targets exist** — wikilinks and explicit links point to valid entry IDs

### Pre-commit hook integration

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: pyrite-schema-validate
      name: Validate KB entries
      entry: .venv/bin/pyrite schema validate
      files: '^kb/.*\.md$'
      types: [markdown]
```

### Output

```
kb/adrs/0017-entry-protocol-mixins.md:
  ✓ Frontmatter valid
  ✓ Type schema: adr
  ✗ ID collision: "entry-protocol-mixins" already exists as backlog_item
  ✓ Required fields present
  ✓ Protocol field types match

kb/backlog/foo.md:
  ✓ Frontmatter valid
  ✗ priority: expected integer, got string "high"
  ✗ Missing required field: effort

2 files checked, 3 errors, 0 warnings
```

Exit code 0 on success, 1 on errors — compatible with pre-commit and CI.

## Files to create/modify

- `pyrite/cli/schema_commands.py` — new `schema validate` subcommand
- `pyrite/cli/__init__.py` — register schema subcommand
- `pyrite/services/validation_service.py` — validation logic (reusable by MCP/API)
- `.pre-commit-config.yaml` — add hook entry
- `tests/test_schema_validate.py` — tests

## Related

- [[entry-id-collision-across-types]] — ID collision would be caught by check #4
- [[sw-adrs-date-field-empty]] — missing date would be caught by check #5
- [[priority-type-mismatch]] — type mismatch would be caught by check #3
