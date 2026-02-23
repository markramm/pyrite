---
type: component
title: "Schema & Validation"
kind: module
path: "pyrite/schema.py"
owner: "markr"
dependencies: ["pyrite.plugins"]
tags: [core, validation]
---

KBSchema defines per-KB validation rules. Validators enforce data quality at write time.

## Key Behaviors
- Plugin validators **always run**, even for types not declared in kb.yaml
- Validators return `list[dict]` with field, rule, expected, got, and optional `severity: "warning"`
- Warnings are advisory; errors block saves when enforce=True
- Quality-gated validation: higher quality levels impose stricter requirements (Encyclopedia pattern)

## Relationship Types
Core relationship types (extends, is_part_of, related_to, owns, etc.) are merged with plugin-provided types. Each has an inverse. `get_inverse_relation()` resolves bidirectionally.
