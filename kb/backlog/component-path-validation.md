---
id: component-path-validation
type: backlog_item
title: "Component path validation against filesystem"
kind: improvement
status: done
priority: medium
effort: S
tags: [software, quality, validation]
links:
  - target: kanban-mcp-tools
    relation: tracks
    note: "Keeps sw_context_for_item data honest"
---

## Problem

Component entries have a `path` field documenting which code path they describe, but nothing verifies that the path still exists. Over time, refactors move code and component docs silently go stale. `sw_context_for_item` then serves misleading information — an agent reads "this component lives at `pyrite/old_module/`" when it's actually been moved.

## Solution

Add a validator to the software-kb plugin that checks component `path` fields against the filesystem during `pyrite index sync` or `pyrite index health`.

### Behavior

- For each `type: component` entry with a non-empty `path` field, check if the path exists (file or directory) relative to the KB root.
- If missing: emit a warning (not an error — the component may document an external dependency or planned module).
- Surface in `pyrite index health` output so stale paths are visible.
- Could also be a programmatic validation entry itself, runnable via `check_command`.

### Scope

This is intentionally small — a single validator function added to `validators.py`. No new types, no new tools. Just keeping existing data honest.
