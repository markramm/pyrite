---
type: design_doc
title: "Structured Data and Schema-as-Config"
status: active
author: markr
date: "2026-02-23"
reviewers: []
tags: [schema, structured-data, plugin, yaml, architecture]
---

# Structured Data and Schema-as-Config

Extend Pyrite's entry model to support structured data objects alongside documents. Users define types with typed fields in `kb.yaml` (no code). Plugins can declare field schemas for auto-validation and UI generation. Migrate to ruamel.yaml for round-trip-safe serialization.

See [ADR-0008](../adrs/0008-structured-data-and-schema.md) for the architectural decision.

---

## The Three-Layer Schema Model

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Plugin Code (Python)                          │
│  Hooks, workflows, MCP tools, computed properties       │
│  Full power. Requires writing a plugin.                 │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Plugin Declared Schema                        │
│  get_field_schemas() returns field definitions           │
│  Auto-validated. Auto-generates UI forms.               │
│  Reduces boilerplate vs pure Python dataclass.          │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Config Schema (kb.yaml)                       │
│  Field types, constraints, select options, object refs  │
│  No code. Users define types in YAML.                   │
│  Uses GenericEntry with automatic field validation.     │
└─────────────────────────────────────────────────────────┘
            ▼ All three produce ▼
┌─────────────────────────────────────────────────────────┐
│  Same Markdown + YAML files in git                      │
└─────────────────────────────────────────────────────────┘
```

### How Types Resolve (Extended)

Current resolution chain: core types → plugin types → GenericEntry.

Extended chain with field schemas:

```
get_entry_class(entry_type)
  1. ENTRY_TYPE_REGISTRY (core Python types)
  2. Plugin get_entry_types() (plugin Python types)
  3. GenericEntry (fallback for config-defined and unknown types)

get_field_schema(entry_type, kb_schema)
  1. kb.yaml types[entry_type].fields (config-defined)
  2. Plugin get_field_schemas()[entry_type] (plugin-declared)
  3. Core CORE_TYPES[entry_type].fields (hardcoded field names, no types yet)
  4. None (no field schema — works like today)
```

A plugin Python type can ALSO have a declared field schema. This means the Python class handles deserialization and behavior, while the field schema handles validation and UI generation. Less boilerplate in validators.

---

## Field Type System

### Supported Types

| Type | YAML Representation | Validation | UI Widget |
|------|-------------------|------------|-----------|
| `text` | `"string value"` | format, min/max length | Text input |
| `number` | `42` or `3.14` | min, max | Number input |
| `date` | `"2026-02-23"` | ISO 8601 date | Date picker |
| `datetime` | `"2026-02-23T14:30:00Z"` | ISO 8601 datetime | Datetime picker |
| `checkbox` | `true` / `false` | boolean | Checkbox |
| `select` | `"option_a"` | must be in options | Dropdown |
| `multi-select` | `["a", "b"]` | each in options | Multi-select |
| `object-ref` | `{ref: "entry-id"}` | target exists, type matches | Entry picker |
| `list` | `[...]` | items validated by inner type | List editor |
| `tags` | `["tag1", "tag2"]` | free-form strings | Tag input |

### Field Definition Schema

```yaml
fields:
  field_name:
    type: text | number | date | datetime | checkbox | select | multi-select | object-ref | list | tags
    required: true | false          # default: false
    default: <value>                # default value for new entries
    description: "Human-readable"   # for UI tooltips and AI agents

    # Type-specific constraints:
    format: email | url | phone     # for text
    min_length: 0                   # for text
    max_length: 500                 # for text
    min: 0                          # for number
    max: 100                        # for number
    options: [a, b, c]              # for select, multi-select
    target_type: person             # for object-ref (optional constraint)
    items: { type: text }           # for list (inner item schema)
```

### Object References

Object references create typed links between entries. They're stored in frontmatter as structured values:

```yaml
# Simple reference
project: { ref: project-alpha }

# List of references
attendees:
  - { ref: jane-doe }
  - { ref: bob-smith }
```

**Indexing:** The DB indexer extracts object-ref fields and stores them in a reference table:

```sql
CREATE TABLE entry_refs (
    source_id TEXT NOT NULL,
    source_kb TEXT NOT NULL,
    field_name TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_type TEXT,           -- from field schema target_type
    UNIQUE(source_id, source_kb, field_name, target_id)
);
CREATE INDEX idx_refs_target ON entry_refs(target_id);
```

This enables:
- Reverse lookups: "which entries reference this person?"
- Relation views: "show all meetings for this project"
- Graph edges: typed relations for Cytoscape visualization
- Backlinks enrichment: show which field the reference came from

**Relationship with existing `links` field:** The existing `links` list (`Link` objects with target, relation, note, kb) remains for freeform semantic links. Object references are structured, typed, field-specific. Both coexist:

| Mechanism | Purpose | Stored In | Typed? |
|-----------|---------|-----------|--------|
| `links` | Semantic relationships (related, cites, refutes) | `links` frontmatter list | Relation string only |
| Object-ref fields | Structural relationships (attendees, project, author) | Named frontmatter fields | By field schema |
| Wikilinks | Inline text references (`[[entry-id]]`) | Body content | No |

---

## Entry Layouts

### Document Layout (Default)

The existing model. Rich frontmatter + substantial Markdown body. The UI shows a full editor with metadata in a sidebar or header.

```yaml
---
id: investigation-corruption-case
type: investigation
title: "City Hall Corruption Case"
status: active
importance: 8
leads:
  - { ref: jane-doe }
  - { ref: bob-smith }
tags: [corruption, city-hall]
---

## Background

Investigation into suspicious contracts awarded by...

## Timeline

- 2026-01-15: Initial tip received
- 2026-01-22: First FOIA request filed
...
```

### Record Layout

Frontmatter-heavy, minimal or empty body. The UI shows a form-first view with property fields, and an optional "notes" area below.

```yaml
---
id: jane-doe
type: person
title: "Jane Doe"
layout: record
role: "City Council Member"
email: "jane.doe@example.gov"
phone: "555-0123"
affiliations:
  - { ref: city-council }
last_contact: "2026-02-20"
status: active
tags: [source, government]
---

Key contact for the city hall investigation. Very cooperative.
```

**The `layout` field** is optional. If omitted, defaults to `document`. The type schema can also declare a default layout:

```yaml
# kb.yaml
types:
  person:
    layout: record
    fields: ...
  investigation:
    layout: document
    fields: ...
```

---

## kb.yaml Extended Format

### Full Example

```yaml
name: investigative-kb
description: "OSINT and investigative journalism knowledge base"
kb_type: investigative

types:
  investigation:
    description: "Active investigation"
    layout: document
    fields:
      status:
        type: select
        options: [planning, active, paused, closed]
        default: planning
        required: true
      importance:
        type: number
        min: 1
        max: 10
      leads:
        type: list
        items: { type: object-ref, target_type: person }
      related_orgs:
        type: list
        items: { type: object-ref, target_type: organization }
    subdirectory: investigations/

  person:
    description: "Person of interest or contact"
    layout: record
    fields:
      role:
        type: text
      email:
        type: text
        format: email
      phone:
        type: text
        format: phone
      affiliations:
        type: list
        items: { type: object-ref, target_type: organization }
      last_contact:
        type: date
      status:
        type: select
        options: [active, inactive, unknown]
        default: unknown
    subdirectory: people/

  meeting:
    description: "Meeting or interview notes"
    layout: document
    fields:
      date:
        type: date
        required: true
      attendees:
        type: list
        items: { type: object-ref, target_type: person }
      meeting_type:
        type: select
        options: [interview, team, briefing, other]
      action_items:
        type: list
        items: { type: text }
    subdirectory: meetings/

policies:
  minimum_sources: 1

validation:
  enforce: true
```

### Backward Compatibility

Existing `kb.yaml` files without `fields` continue to work exactly as before. The `required` and `optional` keys on types are preserved for backward compatibility — they become sugar for field-level `required: true`:

```yaml
# Old format (still works)
types:
  zettel:
    required: ["title"]
    optional: ["zettel_type", "maturity"]
    subdirectory: zettels/

# New format (richer)
types:
  zettel:
    fields:
      zettel_type:
        type: select
        options: [fleeting, literature, permanent, hub]
        default: fleeting
      maturity:
        type: select
        options: [seed, sapling, evergreen]
        default: seed
    subdirectory: zettels/
```

Both formats can coexist in the same `kb.yaml`.

---

## ruamel.yaml Migration

### Why

PyYAML's `safe_dump` does not preserve:
- Comments (stripped on load)
- Blank lines between sections
- Quoting style (single vs double vs unquoted)
- Key ordering beyond insertion order
- Flow vs block style choices

For a git-native tool, this means programmatic edits (adding a tag, updating a date) reformat the entire frontmatter, producing noisy diffs that obscure the actual change.

### Migration Plan

1. Add `ruamel.yaml` to dependencies (replace PyYAML or keep both during transition)
2. Create `pyrite/utils/yaml.py` with wrapper functions:
   ```python
   from ruamel.yaml import YAML

   _yaml = YAML()
   _yaml.preserve_quotes = True
   _yaml.default_flow_style = False

   def load_yaml(text: str) -> dict:
       """Load YAML preserving structure."""
       return _yaml.load(text) or {}

   def dump_yaml(data: dict) -> str:
       """Dump YAML preserving formatting."""
       stream = StringIO()
       _yaml.dump(data, stream)
       return stream.getvalue()

   def load_yaml_file(path: Path) -> dict:
       """Load YAML from file."""
       with open(path) as f:
           return _yaml.load(f) or {}

   def dump_yaml_file(data: dict, path: Path) -> None:
       """Dump YAML to file."""
       with open(path, 'w') as f:
           _yaml.dump(data, f)
   ```
3. Replace all `yaml.safe_load` / `yaml.safe_dump` calls (~12 sites) with wrapper functions
4. Update `Entry.to_markdown()` and `Entry.from_markdown()` to use the new functions
5. Verify round-trip fidelity with tests

### Call Sites to Migrate

| File | Usage |
|------|-------|
| `pyrite/models/base.py:110` | `yaml.safe_dump` in `to_markdown()` |
| `pyrite/models/base.py:120` | `yaml.safe_load` in `from_markdown()` |
| `pyrite/schema.py:437` | `yaml.safe_load` in `KBSchema.from_yaml()` |
| `pyrite/config.py:76,551,569,594` | Config file load/save |
| `pyrite/config.py:495` | GitHub auth load |
| `pyrite/storage/repository.py:55` | Frontmatter parsing in index |
| `pyrite/services/repo_service.py:368` | kb.yaml loading |
| `pyrite/github_auth.py:55,85` | Auth config load/save |

---

## Plugin Integration

### Declaring Field Schemas from Plugins

New optional protocol method:

```python
class PyritePlugin(Protocol):
    # ... existing methods ...

    def get_field_schemas(self) -> dict[str, dict[str, dict]]:
        """Return field schemas for entry types.

        Returns:
            Dict mapping type name to field definitions.
            Each field definition matches the kb.yaml fields format.

        Example:
            {"zettel": {
                "zettel_type": {"type": "select", "options": [...], "default": "fleeting"},
                "maturity": {"type": "select", "options": [...], "default": "seed"},
            }}
        """
        ...
```

This is optional. Plugins that don't implement it continue to work. Plugins that do get:
- Automatic field validation (no need to write a validator for basic type checks)
- UI form generation in the web app
- Schema exposure to MCP tools and AI agents
- Documentation generation

### How Plugin Schemas Interact with kb.yaml

kb.yaml can override plugin field schemas per-KB:

```yaml
# kb.yaml — override zettel plugin's maturity options for this KB
types:
  zettel:
    fields:
      maturity:
        options: [seed, sapling, tree, evergreen]  # Added "tree" level
```

Resolution order: kb.yaml field overrides → plugin declared schema → core type defaults.

---

## Implementation Phases

### Phase A: Foundation (Effort: M)

**Schema-as-Config core:**
- Extend `TypeSchema` with `fields: dict[str, FieldSchema]` and `layout: str`
- Create `FieldSchema` dataclass with type, required, default, constraints
- Update `KBSchema.from_dict()` to parse field definitions
- Update `KBSchema.validate_entry()` to validate against field schemas
- Add `get_field_schemas()` to plugin protocol (optional method)
- Update `to_agent_schema()` to include field type information

**Files:** `pyrite/schema.py`, `pyrite/plugins/protocol.py`

### Phase B: ruamel.yaml Migration (Effort: S)

- Add `ruamel.yaml` dependency
- Create `pyrite/utils/yaml.py` with wrapper functions
- Migrate all 12 call sites
- Add round-trip fidelity tests
- Remove PyYAML dependency (or keep as fallback)

**Files:** `pyproject.toml`, `pyrite/utils/yaml.py` (new), all files with `yaml.safe_load`/`yaml.safe_dump`

### Phase C: Object References and Indexing (Effort: M)

- Add `entry_refs` table to DB schema
- Update indexer to extract object-ref fields using field schemas
- Add reverse lookup queries (`get_references_to(entry_id)`)
- Update backlinks API to include object-ref sources
- Update graph data to include object-ref edges

**Files:** `pyrite/storage/database.py`, `pyrite/storage/index.py`, `pyrite/server/endpoints/entries.py`

### Phase D: Web UI Integration (Effort: L)

- Auto-generate entry forms from field schemas
- Record layout: form-first view with optional notes area
- Document layout: metadata sidebar with typed field editors
- Select/multi-select dropdowns, date pickers, entry pickers for object-refs
- Database views use field types for column rendering

**Files:** `web/src/lib/components/entry/` (new form components), `web/src/routes/entries/[id]/+page.svelte`

### Phase E: Plugin Schema Declaration (Effort: S)

- Add `get_field_schemas()` to existing extensions (zettelkasten, social, encyclopedia)
- Update extension builder skill to scaffold field schemas
- Merge plugin schemas with kb.yaml overrides in validation

**Files:** Extension plugin.py files, `.claude/skills/pyrite-dev/extensions.md`

---

## Relationship to Existing Backlog Items

| Backlog Item | Relationship |
|-------------|-------------|
| **Dataview-Style Queries** (#31) | Field types enable typed filtering/sorting in queries |
| **Database Views** (#32) | Field types determine column rendering and edit widgets |
| **Extension Builder Skill** (in progress) | Scaffold types with field schemas |
| **Wikilinks** (#1) | Object-ref fields complement inline wikilinks |
| **Backlinks Panel** (#3) | Enriched with object-ref source field names |
| **Knowledge Graph** (#13) | Object-ref edges add typed relations to graph |
| **MCP Prompts and Resources** (#9) | Typed schemas improve AI agent data creation |

---

## Verification

After each phase:

1. `pytest tests/` — all backend tests pass
2. Existing entries load/save without changes (backward compat)
3. New field-schema-defined types validate correctly
4. Round-trip test: load YAML → modify one field → save → diff shows only that field
5. Object-ref reverse lookups return correct results
6. Web UI renders forms for schema-defined types
7. Extension builder skill generates types with field schemas
