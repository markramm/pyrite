---
type: adr
title: "Type Metadata, AI Instructions, and Plugin Documentation"
adr_number: 9
status: accepted
deciders: ["markr"]
date: "2026-02-23"
tags: [architecture, types, plugins, ai-agents, documentation]
---

# ADR-0009: Type Metadata, AI Instructions, and Plugin Documentation

## Context

Pyrite has a well-layered type system (ADR-0002, ADR-0008) with three sources of types: core dataclasses, plugin entry types, and config-only types in kb.yaml. The boundaries between KB policy and plugin-contributed types are clean — plugins define types and behavior, KB config defines local policies and validation rules.

However, several gaps emerge when we examine how types interact with the broader system:

### Gap 1: Types are opaque to AI agents

When an AI agent (via MCP, Claude Code skill, or web AI) encounters a KB with types like `zettel`, `article`, or `meeting`, it has no guidance on:
- What this type represents and when to create one
- What good data looks like (field descriptions, examples)
- Domain-specific methodology (e.g., zettelkasten's CEQRC workflow)
- Relationships to other types (e.g., "a literature_note should reference a zettel")

The agent must either guess from field names or the user must explain in every prompt. This is the difference between an agent that can participate in a research methodology and one that can only do generic CRUD.

### Gap 2: Config-only types are second-class

ADR-0008 introduces rich field types in kb.yaml, but even with those, config-only types lack:
- Human-readable field descriptions ("attendees" → "People present at the meeting")
- AI instructions for the type
- Display hints for UI rendering
- Default sort/group/filter preferences

The jump from "I declared a type in kb.yaml" to "I wrote a Python plugin" is too large. There should be a middle ground where config alone produces a well-documented, AI-friendly type.

### Gap 3: Plugin documentation is implicit

The plugin protocol (11 methods) is well-documented in code, and three proof-of-concept extensions exist. But there is no cohesive guide that covers:
- How to build a plugin from scratch
- Patterns learned from the three existing extensions
- How plugin types surface across CLI, API, MCP, and web UI
- How types, validators, hooks, and workflows compose
- Common pitfalls and testing strategies

### Gap 4: Types don't declare how they surface

A plugin can register entry types, CLI commands, MCP tools, validators, hooks, workflows, and DB tables — but there's no declarative way to express:
- "Events should default to a calendar/timeline view"
- "Records should show form-first, documents should show editor-first"
- "This type's entries should be listed by date descending, not title"
- "The sidebar should show these fields as a summary card"

These UI/workflow hints currently require either plugin code (for plugins) or nothing (for config types).

### What we have (and what's working)

Before addressing the gaps, it's worth noting the clean boundaries that already exist:

| Concern | Owned by | Mechanism |
|---------|----------|-----------|
| Type definition (fields, validation) | Core types OR plugin `get_entry_types()` OR kb.yaml | `get_entry_class()` lookup chain |
| KB-level policy (min sources, enforcement) | kb.yaml `policies:` section | `KBSchema.validate_entry()` |
| Domain-specific validation | Plugin `get_validators()` | Always runs, even for core types |
| CLI commands | Plugin `get_cli_commands()` | Registered at startup |
| MCP tools | Plugin `get_mcp_tools(tier)` | Per-tier registration |
| Lifecycle behavior | Plugin `get_hooks()` | before/after save/delete |
| State machines | Plugin `get_workflows()` | Transition rules per field |

**Plugins don't own KB policy, and KB policy doesn't require plugins.** This separation is correct and should be preserved.

## Decision

### 1. Type Metadata Block

Add an optional `metadata` section to type definitions (both kb.yaml and plugin-declared schemas) that carries human and AI-readable information:

```yaml
# In kb.yaml
types:
  meeting:
    description: "Record of a meeting with attendees, decisions, and action items"
    layout: record
    ai_instructions: |
      Create a meeting entry when the user describes a meeting, call, or group discussion.
      Always capture: date, attendees (as object-refs to person entries), key decisions.
      Action items should be a checklist in the body. If attendees aren't in the KB yet,
      create person entries for them first.
      Meetings are part of an investigation's evidence chain — link to the relevant
      investigation entry.
    fields:
      date:
        type: date
        required: true
        description: "When the meeting occurred"
      attendees:
        type: list
        items: { type: object-ref, target_type: person }
        description: "People present at the meeting"
      status:
        type: select
        options: [scheduled, completed, cancelled]
        default: scheduled
      decision_summary:
        type: text
        description: "Brief summary of key decisions made"
    display:
      default_sort: date_desc
      card_fields: [date, status, attendees]
      icon: calendar
    subdirectory: meetings/
```

The three new sections are:
- **`ai_instructions`** — Free-text guidance for AI agents on when and how to create/update this type. Injected into MCP tool descriptions and Claude Code skill context.
- **Field `description`** — Per-field human-readable descriptions. Used in UI form labels, API docs, and AI context.
- **`display`** — Declarative UI hints. Not prescriptive — the UI can ignore them. But they allow config-only types to express rendering preferences without code.

### 2. Plugin-Declared Type Metadata

Plugins can provide the same metadata via a new optional protocol method:

```python
def get_type_metadata(self) -> dict[str, dict]:
    """
    Return metadata for plugin-defined types.

    Returns:
        Dict mapping type name to metadata dict.
        Each metadata dict can contain:
            ai_instructions: str — guidance for AI agents
            display: dict — UI rendering hints
            field_descriptions: dict[str, str] — per-field descriptions

    Example:
        {
            "zettel": {
                "ai_instructions": "Create a zettel for atomic, reusable ideas...",
                "display": {
                    "default_sort": "updated_desc",
                    "card_fields": ["zettel_type", "maturity"],
                },
                "field_descriptions": {
                    "zettel_type": "Classification: fleeting, literature, permanent, or hub",
                    "maturity": "Growth stage: seed → sapling → evergreen",
                },
            }
        }
    """
```

Plugin types that already have Python dataclass fields get descriptions from docstrings or this method. Config types get descriptions from the YAML. Both produce the same runtime metadata.

### 3. Metadata Resolution Order

When the system needs type metadata (e.g., to build an MCP tool description or a UI form):

1. **kb.yaml overrides** — Local KB can override any type's metadata (even plugin types)
2. **Plugin `get_type_metadata()`** — Plugin-provided defaults
3. **Plugin dataclass introspection** — Field names, types, defaults from the Python class
4. **Core type defaults** — Built-in descriptions for the 8 core types

This lets a KB customize a plugin type's AI instructions for their domain without modifying the plugin.

### 4. AI Context Injection

Type metadata flows into AI surfaces automatically:

**MCP tools:** `kb_create` and `kb_schema` include type metadata in their responses:
```json
{
  "type": "meeting",
  "description": "Record of a meeting with attendees, decisions, and action items",
  "ai_instructions": "Create a meeting entry when the user describes...",
  "fields": {
    "date": {"type": "date", "required": true, "description": "When the meeting occurred"},
    "attendees": {"type": "list", "description": "People present at the meeting"}
  }
}
```

**Claude Code skills:** The KB skill injects type metadata when creating entries, so the agent knows what fields to populate and what methodology to follow.

**Web AI:** The `/api/ai/generate` endpoint uses type metadata to guide entry generation.

### 5. Display Hints (Declarative, Not Prescriptive)

The `display` block is a vocabulary of hints the UI can use:

| Hint | Values | Used by |
|------|--------|---------|
| `default_sort` | `date_desc`, `date_asc`, `title_asc`, `updated_desc`, `created_desc` | Entry list, sidebar |
| `card_fields` | list of field names | Sidebar card, search results |
| `icon` | string (icon name from icon set) | Sidebar, breadcrumbs |
| `color` | string (CSS color or theme token) | Type badges, graph nodes |
| `preferred_view` | `editor`, `form`, `split`, `table` | Entry page default layout |
| `group_by` | field name | Default grouping in list view |

These are **hints, not contracts**. The web UI reads them for defaults; CLI and MCP ignore them. A type without display hints renders with sensible defaults. This avoids coupling type definitions to UI implementation.

### 6. Plugin Developer Guide

Create comprehensive plugin documentation based on patterns from the three existing extensions (Zettelkasten, Social, Encyclopedia). The guide covers:

1. **Plugin structure** — Entry point registration, plugin class, minimal vs full plugin
2. **Entry types** — Dataclass patterns, from_frontmatter/to_frontmatter, validation
3. **Type metadata** — AI instructions, field descriptions, display hints
4. **Integration points** — How types surface in CLI, API, MCP, web UI
5. **Hooks and workflows** — Lifecycle hooks, state machines, permission patterns
6. **DB tables** — When to use custom tables vs metadata, indexing patterns
7. **Testing** — Test patterns from the extensions, fixture strategies
8. **Common patterns** — Folder-per-author, engagement layer, KB presets

### 7. KB Policy Stays Separate

This ADR explicitly does **not** move KB policy into types or plugins:

- `policies.minimum_sources` remains a KB-level setting
- `validation.enforce` remains a KB-level setting
- `validation.rules` (range, format) remain KB-level
- Plugin validators can enforce domain rules but don't set KB policy

A plugin can _recommend_ policies via `get_kb_presets()`, but the KB owner decides whether to adopt them. This preserves the principle that **KB policy is a local decision, not a plugin decision**.

## Consequences

### Positive

- AI agents get rich, type-aware context without per-prompt instruction
- Config-only types become first-class with descriptions, AI instructions, and display hints
- The gap between "kb.yaml type" and "Python plugin type" narrows significantly
- Plugin developers get a comprehensive guide and clear patterns
- UI can render intelligent defaults without hardcoding type knowledge
- KB owners can customize type behavior locally by overriding metadata in kb.yaml
- MCP tool responses become self-documenting for any MCP client

### Negative

- `ai_instructions` is free text — quality depends on who writes it
- Display hints add another optional config surface that could confuse new users
- Type metadata resolution (4 layers) adds complexity to the lookup path
- Plugin developer guide requires ongoing maintenance as the protocol evolves

### Risks

- AI instructions could become stale if type behavior changes (mitigated: instructions live next to the type definition)
- Display hints could create implicit UI contracts that constrain future UI changes (mitigated: hints are non-binding)
- Over-specifying type metadata in kb.yaml could make config files unwieldy (mitigated: all sections are optional)

## Related

- **ADR-0002**: Plugin system via entry points — extended with `get_type_metadata()`
- **ADR-0008**: Structured data and schema-as-config — field descriptions and AI instructions build on rich field types
- **ADR-0007**: AI integration architecture — type metadata feeds all three AI surfaces
- **Backlog**: Type Metadata and AI Instructions, Plugin Developer Guide, Display Hints for Types
