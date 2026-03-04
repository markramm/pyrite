---
id: schema-module-decomposition
type: backlog_item
title: "Decompose schema.py kitchen-sink module"
kind: improvement
status: proposed
milestone: "0.18"
priority: medium
effort: M
tags: [architecture, code-quality]
links:
- structured-data-schema
---

# Decompose schema.py kitchen-sink module

## Problem

`pyrite/schema.py` is 1,157 lines mixing 4+ distinct concerns:

1. **Data models** — `Source`, `Link`, `Provenance` dataclasses (belong in `models/`)
2. **Type metadata** — `CORE_TYPES`, `CORE_TYPE_METADATA` dicts (configuration data)
3. **Validation** — `validate_entry()`, `validate_frontmatter()`, field validators
4. **ID generation** — `generate_entry_id()`, `slugify()`
5. **Schema-as-config** — `FieldSchema`, `TypeSchema`, `KBSchema` dataclasses

A caller importing `from pyrite.schema import Link` also transitively loads type metadata, validation logic, and ID generation code they don't need.

## Solution

Split into focused modules:

| Module | Contents |
|--------|----------|
| `pyrite/models/links.py` | `Source`, `Link`, `Provenance` dataclasses |
| `pyrite/schema/types.py` | `CORE_TYPES`, `CORE_TYPE_METADATA`, type registry |
| `pyrite/schema/validation.py` | `validate_entry()`, `validate_frontmatter()`, validators |
| `pyrite/schema/config.py` | `FieldSchema`, `TypeSchema`, `KBSchema` |
| `pyrite/schema/ids.py` | `generate_entry_id()`, `slugify()` |
| `pyrite/schema/__init__.py` | Re-exports for backward compatibility |

## Approach

1. Create `pyrite/schema/` package with `__init__.py` re-exporting all current public names
2. Move code to submodules one concern at a time
3. Backward-compat: `from pyrite.schema import Link` continues to work via `__init__.py`
4. Update internal imports to use specific submodules over time

## Files likely affected

- `pyrite/schema.py` → `pyrite/schema/__init__.py` + submodules
- `pyrite/models/links.py` — new
- All files importing from `pyrite.schema` (no changes needed if `__init__.py` re-exports)

## Success criteria

- No single file > 400 lines
- Each submodule has a single, clear purpose
- All existing imports continue to work
- No test changes required (backward-compat re-exports)
