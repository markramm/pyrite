---
type: component
title: "Schema & Validation"
kind: module
path: "pyrite/schema.py"
owner: "markr"
dependencies: ["pyrite.plugins"]
tags: [core, validation]
---

`KBSchema` defines per-KB validation rules loaded from `kb.yaml`. The module also houses core data classes (`Source`, `Link`, `Provenance`), enums (`VerificationStatus`, `EventStatus`, `ResearchStatus`), and the `CORE_TYPES` / `CORE_TYPE_METADATA` registries.

## Validator Lifecycle

1. `KBSchema.from_yaml(path)` loads the KB's `kb.yaml` and parses type definitions into `TypeSchema` objects with `FieldSchema` fields.
2. On write, `validate_entry(entry_type, fields, context)` runs validation:
   - Checks required fields from `TypeSchema.required`
   - Validates typed field values via `_validate_field_value()` (supports 10 types: text, number, date, datetime, checkbox, select, multi-select, object-ref, list, tags)
   - Applies `validation.rules` from kb.yaml (range checks, ISO8601 format)
   - Checks `policies.minimum_sources`
   - Runs plugin validators (always, even for unknown types)
3. Returns `{"valid": bool, "errors": [...], "warnings": [...]}`.

## Enforcement Modes

- **Advisory** (default): field type mismatches become warnings with `severity: "warning"`. Entries are saved.
- **Enforced** (`validation.enforce: true` in kb.yaml): mismatches become errors that block saves.
- Unknown entry types produce errors only when enforce is true.

## Schema Versioning

Schemas evolve via version tracking and on-load migration. Three version markers:

- **`KBSchema.schema_version`** — top-level version in kb.yaml, increments when any type changes
- **`TypeSchema.version`** — per-type version in kb.yaml (e.g., `version: 3`)
- **`FieldSchema.since_version`** — marks when a required field was introduced

### Version-Aware Validation

`validate_entry()` checks `_schema_version` in the context dict. When a required field has `since_version` set and the entry's schema version predates it, the missing-field error is downgraded to a warning. Entries at or above the `since_version` get the normal error.

### Migration Registry

`pyrite/migrations.py` provides `MigrationRegistry` with decorator-based registration. Migrations operate on raw frontmatter dicts (before Entry construction). Chain resolution sorts by `from_version` and raises `ValueError` on gaps.

`KBRepository._maybe_migrate()` applies pending migrations on load. `KBRepository.save()` stamps `_schema_version` with the current type version.

### CLI Commands

- `pyrite schema diff --kb <name>` — shows types with version annotations and `since_version` highlights
- `pyrite schema migrate --kb <name> [--dry-run]` — forces load+save of all entries, applying migrations

## Plugin Validator Registration

Plugins implement `get_validators() -> list[Callable]`. Each validator receives `(entry_type, fields, context)` and returns `list[dict]` with keys: `field`, `rule`, `expected`, `got`, optional `severity`.

Validators are collected via `get_registry().get_all_validators()` and called in registration order. The system gracefully falls back to the old `(entry_type, data)` two-argument signature for backwards compatibility.

## Quality-Gated Validation

The Encyclopedia extension demonstrates quality-gated validation: higher `research_status` levels (stub → partial → draft → complete → published) impose stricter requirements. For example, `published` articles must have minimum sources, proper citations, and verified provenance.

## Type Metadata Resolution

`resolve_type_metadata(type_name, kb_schema)` merges metadata from 4 layers (lowest → highest priority):

1. `CORE_TYPE_METADATA` — built-in defaults (8 core types + collection)
2. Plugin `get_type_metadata()` — domain-specific overrides
3. `TypeSchema` from kb.yaml — KB-level customization
4. (Empty defaults as base)

Returns: `ai_instructions`, `field_descriptions`, `display` dict.

## Relationship Types

`RELATIONSHIP_TYPES` defines ~30 core relationship types, each with an inverse (e.g., `owns` ↔ `owned_by`, `supports` ↔ `supported_by`). Includes both entity relationships (employment, funding, membership) and Zettelkasten note relationships (supports, contradicts, extends, refines).

`get_all_relationship_types()` merges core types with plugin-provided types via `get_registry().get_all_relationship_types()`. `get_inverse_relation()` resolves inverses bidirectionally, defaulting to `related_to`.

## Agent Schema Export

`to_agent_schema()` serializes the full schema for MCP's `kb_schema` tool: all core + custom types with fields, AI instructions, field descriptions, display hints, and relationship types. Used by AI agents to discover what they can create.

## Related

- [[entry-model]] — data classes that schema validates
- [[kb-service]] — calls `validate_entry()` on create/update
- [[mcp-server]] — `kb_schema` tool exposes schema to agents
