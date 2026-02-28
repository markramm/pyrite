---
id: extension-init-cli
title: "pyrite extension init CLI Command"
type: backlog_item
tags:
- feature
- cli
- extensions
- agent-infrastructure
kind: feature
priority: high
effort: S
status: proposed
---

## Problem

The extension-builder skill provides instructions for scaffolding a new extension, but the actual directory creation, pyproject.toml generation, and boilerplate file creation must be done manually (or by an agent following the skill's text instructions). An autonomous agent building a domain-specific extension needs a CLI command that does the mechanical setup, so the skill becomes documentation for *how to fill in* the scaffold rather than instructions the agent must execute step by step.

## Proposed Solution

### `pyrite extension init` command

```bash
# Scaffold a new extension
pyrite extension init legal --path extensions/legal

# With entry types pre-declared
pyrite extension init legal --path extensions/legal \
  --types case,statute,ruling,party

# With description for plugin metadata
pyrite extension init legal --path extensions/legal \
  --description "Legal research domain types and tools"
```

### Generated structure

```
extensions/legal/
  pyproject.toml                  # With entry point, hatchling build
  src/pyrite_legal/
    __init__.py
    plugin.py                     # Plugin class skeleton with get_entry_types, get_validators
    entry_types.py                # Dataclass skeletons for declared types
    validators.py                 # Validator skeleton (returns [] for unrelated types)
    preset.py                     # Preset skeleton
  tests/
    test_legal.py                 # 8-section test skeleton
```

### Behavior

- Generates valid, importable Python that passes ruff and basic pytest
- Pre-populates the entry type skeletons with `entry_type` property, `to_frontmatter`, `from_frontmatter`
- Test file includes `TestPluginRegistration` with correct plugin name
- Validator includes the critical "return [] for unrelated types" pattern
- `--format json` returns the list of created files

### Why separate from the skill

The skill knows *what* a good extension looks like (architecture, patterns, gotchas). The CLI command handles *file creation mechanics*. Together: the agent runs `pyrite extension init`, then uses the skill to fill in the real logic, then uses pyrite-dev's TDD protocol to test it.

## Related

- [[bhag-self-configuring-knowledge-infrastructure]] — Agent-built extensions
- [[extension-builder-skill]] — Skill for the design/implementation phase
