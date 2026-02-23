---
type: standard
title: "Extension Development Standards"
category: coding
enforced: false
tags: [extensions, plugins]
---

## Package Structure
```
extensions/<name>/
  pyproject.toml          # declares pyrite.plugins entry point
  src/pyrite_<name>/
    __init__.py
    plugin.py             # main plugin class
    entry_types.py         # dataclass Entry subclasses
    validators.py          # validation callables
    cli.py                 # typer sub-app
    preset.py              # KB preset definition
    workflows.py           # state machines (if needed)
    hooks.py               # lifecycle hooks (if needed)
    tables.py              # custom DB table defs (if needed)
  tests/
    test_<name>.py
```

## Entry Type Rules
- Subclasses MUST override `from_frontmatter()` to map custom fields
- `to_frontmatter()` MUST set `meta["type"]` and SHOULD omit default values
- Use helper for common NoteEntry kwargs to reduce boilerplate

## Validator Rules
- Return `[]` for unrelated entry types (type-dispatched)
- Use severity="warning" for advisory checks
- DB table names MUST be prefixed with plugin name to avoid collisions

## CLI Rules
- CLI module imported lazily inside `get_cli_commands()` to handle missing typer
- Dependencies list should be empty — pyrite is a peer dependency
