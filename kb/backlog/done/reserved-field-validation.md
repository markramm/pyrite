---
id: reserved-field-validation
type: backlog_item
title: "Reserved Field Name Validation"
kind: improvement
status: completed
milestone: "0.18"
priority: medium
effort: S
tags: [schema, validation, field-system]
---

# Reserved Field Name Validation

## Problem

Users could define custom fields in kb.yaml with names that collide with reserved Entry base fields (e.g., `summary`, `body`, `id`). This caused silent data corruption — the custom FieldSchema definition would shadow the core field's behavior.

## Solution

- New `pyrite/schema/reserved.py` with `RESERVED_FIELD_NAMES` frozenset (~30 names)
- `KBSchema.from_dict()` warns and strips colliding field definitions
- Protocol fields (status, priority, date, etc.) are NOT reserved — users legitimately define validation constraints on them
- Fixed `_KNOWN_KEYS` in `generic.py` — `importance` and `lifecycle` were missing, causing them to silently land in metadata
- Extracted `PROTOCOL_COLUMN_KEYS` constant from inline set in IndexManager

## Files modified

- `pyrite/schema/reserved.py` — new: RESERVED_FIELD_NAMES
- `pyrite/schema/kb_schema.py` — collision validation in from_dict()
- `pyrite/schema/__init__.py` — export RESERVED_FIELD_NAMES
- `pyrite/models/generic.py` — _KNOWN_KEYS fix + from_frontmatter importance/lifecycle
- `pyrite/models/protocols.py` — PROTOCOL_COLUMN_KEYS constant
- `pyrite/storage/index.py` — use PROTOCOL_COLUMN_KEYS

## Success criteria

- Custom fields named `summary`, `body`, etc. get stripped with warning
- Protocol fields (status, priority) can still be defined in kb.yaml
- GenericEntry correctly handles importance/lifecycle from frontmatter
- 11 new tests, all 1834 tests pass
