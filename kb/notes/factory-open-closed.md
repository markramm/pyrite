---
id: factory-open-closed
title: "Fix factory.py Open-Closed violation"
type: backlog_item
tags: [architecture, models, code-quality]
links:
- target: entry-factory-deduplication
  relation: related
kind: improvement
status: done
effort: S
---

# Fix factory.py Open-Closed violation

## Problem

`pyrite/models/factory.py` has a 70-line if/elif chain that hard-codes constructor mappings for 5 core entry types (`EventEntry`, `PersonEntry`, etc.) before falling through to the `ENTRY_TYPE_REGISTRY` lookup. Each branch manually maps kwargs to constructor parameters:

```python
if entry_type == "event":
    return EventEntry.create(title=title, date=date, body=body, ...)
elif entry_type == "person":
    return PersonEntry.create(name=title, role=metadata.get("role"), ...)
```

Adding a new core type requires editing this file — violating Open-Closed Principle. The `ENTRY_TYPE_REGISTRY` fallback (line 110) and plugin class fallback (line 126) already handle arbitrary types correctly. The 5 hard-coded branches are redundant.

## Solution

Remove the hard-coded if/elif chain. All core types should go through `ENTRY_TYPE_REGISTRY` the same way plugin types do. Each entry type's `create()` classmethod should handle its own constructor signature normalization (most already do).

Where `create()` signatures differ from the generic kwargs pattern, add a `from_kwargs(cls, **kwargs)` classmethod to the entry type that handles the mapping.

## Files likely affected

- `pyrite/models/factory.py` — remove if/elif, use registry for all types
- `pyrite/models/core_types.py` — ensure `create()` classmethods accept generic kwargs
- Possibly entry type classes that have unusual constructor signatures

## Success criteria

- `build_entry()` has no type-specific if/elif branches
- All types resolve through the registry
- Adding a new core type requires zero changes to factory.py
- All existing entry creation tests pass
