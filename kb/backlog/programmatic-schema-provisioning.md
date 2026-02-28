---
id: programmatic-schema-provisioning
title: "Programmatic Schema Provisioning via MCP and CLI"
type: backlog_item
tags:
- feature
- mcp
- agent-infrastructure
kind: feature
priority: medium
effort: M
status: done
---

## Problem

A legal research agent doesn't want to hand-write `kb.yaml`. It wants to call an MCP tool or CLI command and say "create me a KB with case, statute, ruling, and party types with these fields." The current admin MCP tools (`kb_manage`) can create and remove KBs, but cannot define custom types and field schemas programmatically.

## Proposed Solution

### MCP tools (admin tier)

```
kb_schema_update(kb, types={
  "case": {
    "description": "Legal case or proceeding",
    "fields": {
      "jurisdiction": {"type": "select", "options": ["federal", "state"]},
      "status": {"type": "select", "options": ["active", "decided", "appealed"]},
      "filing_date": {"type": "date"},
      "parties": {"type": "list", "items": {"type": "text"}}
    }
  }
})
```

### CLI equivalent

```bash
pyrite kb schema update --kb legal \
  --type case \
  --field "jurisdiction:select:federal,state,international" \
  --field "status:select:active,decided,appealed,settled" \
  --field "filing_date:date" \
  --field "parties:list:text"
```

Or the full-schema approach:

```bash
pyrite kb schema set --kb legal --schema-file types.yaml
```

### Behavior

- Validates the schema definition before writing
- Merges with existing kb.yaml (additive by default)
- Rebuilds index to pick up new type definitions
- Returns the full schema as confirmation
- `--format json` support

### Why this matters

Without programmatic schema provisioning, the agent self-configuration loop has a gap: the agent can build an extension (code), but can't configure a KB to use that extension's types without editing YAML files. This bridges that gap.

## Related

- [[headless-kb-init]] — Creates a KB; this command configures its schema after creation
- [[bhag-self-configuring-knowledge-infrastructure]] — Schema-as-API for agents
