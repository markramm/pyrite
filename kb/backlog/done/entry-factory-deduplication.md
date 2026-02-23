---
type: backlog_item
title: "Extract Entry Factory to Eliminate Duplicated Construction Logic"
kind: improvement
status: completed
priority: high
effort: S
tags: [refactoring, dx]
---

Entry construction — a 50+ line if/elif chain mapping entry types to constructors with type-specific kwargs — is duplicated in **three** places:
- `KBService.create_entry()` (kb_service.py:124-191)
- `PyriteMCPServer._kb_create()` (mcp_server.py:485-542)
- `endpoints/entries.py create_entry()` (entries.py:149-230)

Any new entry type with special constructor kwargs must be added to all three locations, and they can drift out of sync.

Also: the KB config lookup pattern (`for kbc in config.knowledge_bases: if kbc.name == kb:`) is repeated 4x in entries.py when `config.get_kb()` already exists.

## Fix

Extract a `build_entry(entry_type: str, **kwargs) -> Entry` factory function in `pyrite/models/factory.py` that all call sites use. The factory should consult the plugin registry for plugin-provided entry types.

## Acceptance Criteria

- [ ] Single `build_entry()` function handles all entry type dispatch
- [ ] All three call sites use the factory
- [ ] KB lookup uses `config.get_kb()` instead of inline loops
- [ ] Existing tests pass without changes
