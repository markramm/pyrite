---
id: schema-service
title: Schema Service
type: component
kind: service
path: pyrite/services/schema_service.py
owner: core
dependencies:
- pyrite.config
- pyrite.schema
tags:
- core
- service
---

Programmatic management of kb.yaml type schemas. Provides add, remove, show, and set operations for type definitions without manual YAML editing.

## Key Methods

- `add_type(kb_name, type_name, definition)` — adds a type definition to kb.yaml
- `remove_type(kb_name, type_name)` — removes a type definition
- `show_schema(kb_name)` — returns the full schema for a KB
- `set_field(kb_name, type_name, field_name, field_def)` — adds/updates a field on a type

## Consumers

- CLI: `pyrite schema diff`, `pyrite schema migrate`
- MCP: `kb_schema` tool (read), `kb_manage` tool (write)

## Related

- [[schema-validation]] — KBSchema that this service manages
- [[config-system]] — KBConfig provides path to kb.yaml
