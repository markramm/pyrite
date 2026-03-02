---
type: component
title: "Entry Model"
kind: module
path: "pyrite/models/"
owner: "markr"
dependencies: ["pyrite.schema"]
tags: [core, data-model]
---

The entry model defines the base data classes for all knowledge entries. Located in `pyrite/models/`, it provides the type system that the rest of the platform builds on.

## Key Files

- `base.py` — `Entry` abstract base dataclass and parsing utilities
- `core_types.py` — 10 built-in types + `ENTRY_TYPE_REGISTRY` + `get_entry_class()` + `entry_from_frontmatter()`
- `collection.py` — `CollectionEntry` for folder-backed and virtual collections (added in 0.3)
- `generic.py` — `GenericEntry` fallback for unknown/plugin types
- `factory.py` — `build_entry()` factory for programmatic creation

## Entry Base Class

`Entry` (abstract dataclass) provides the shared contract:

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier (auto-generated from title or date) |
| `title` | str | Display title |
| `body` | str | Markdown content |
| `summary` | str | One-line summary |
| `tags` | list[str] | Categorization tags |
| `links` | list[Link] | Typed relationships to other entries |
| `sources` | list[Source] | Provenance references |
| `provenance` | Provenance | Who created/modified and when |
| `metadata` | dict | Extension fields for custom types |
| `created_at` | datetime | UTC creation timestamp |
| `updated_at` | datetime | UTC modification timestamp |
| `kb_name` | str | KB reference (set when loaded) |
| `file_path` | Path | Filesystem path (set when loaded) |
| `_schema_version` | int | Schema version when entry was created/migrated (0 = unversioned) |

Abstract methods: `entry_type` (property), `to_frontmatter()`, `from_frontmatter()`.

Concrete methods: `_base_frontmatter()`, `to_db_dict()`, `to_markdown()`, `from_markdown()`, `load()`, `save()`, `add_link()`, `add_source()`, `validate()`.

## Core Types (10)

| Type | Class | Key Fields |
|------|-------|------------|
| note | `NoteEntry` | (base only) |
| person | `PersonEntry` | role, affiliations, importance, research_status |
| organization | `OrganizationEntry` | org_type, jurisdiction, founded, importance |
| event | `EventEntry` | date, importance, status, location, participants |
| document | `DocumentEntry` | date, author, document_type, url, importance |
| topic | `TopicEntry` | importance |
| relationship | `RelationshipEntry` | source_entity, target_entity, relationship_type |
| timeline | `TimelineEntry` | date_range |
| collection | `CollectionEntry` | source_type, query, description, icon, view_config, folder_path |
| qa_assessment | `QAAssessmentEntry` | assessment_type, target_entry, severity, status |

## CollectionEntry (Added in 0.3)

Represents both folder-backed (`source_type="folder"`) and virtual (`source_type="query"`) collections. Key methods:

- `from_collection_yaml(yaml_data, folder_path)` — creates from `__collection.yaml` files
- `from_frontmatter(meta, body)` — standard entry loading
- `to_frontmatter()` — serializes only non-default fields

Virtual collections store their query DSL string in the `query` field.

## Type Resolution

`get_entry_class(type_name)` resolves in order:
1. `ENTRY_TYPE_REGISTRY` — 9 core types
2. `get_registry().get_all_entry_types()` — plugin-provided types
3. `GenericEntry` — fallback that stores `_entry_type` and `metadata`

`entry_from_frontmatter(meta, body)` reads `meta["type"]` (default: "note"), resolves the class, and calls `from_frontmatter()`.

## Factory

`build_entry(entry_type, *, entry_id, title, body, **kwargs)` in `factory.py` handles programmatic creation with type-specific field mapping. Used by `KBService.create_entry()` and MCP `kb_create` tool. Falls back to plugin types via `from_frontmatter()`, then `GenericEntry`.

## Extension Pattern

Plugin entry types extend `NoteEntry` or `DocumentEntry`. Must override:
- `entry_type` property — return the type string
- `from_frontmatter(meta, body)` — map custom fields from meta
- `to_frontmatter()` — call `_base_frontmatter()` then add custom fields

Register via plugin's `get_entry_types() -> dict[str, type[Entry]]`.

## Related

- [[schema-validation]] — validates entries against `KBSchema`
- [[kb-service]] — CRUD operations on entries
- [[collection-query-service]] — evaluates virtual collection queries
