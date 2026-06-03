---
id: task-parent-child-link-enforcement
type: backlog_item
title: "Enforce bidirectional parent/child task links (backlinks from parent epic to children)"
kind: feature
status: proposed
priority: low
effort: M
tags: [task-system, schema, conductor-workflow, epic-tracking, integrity]
---

## Problem

`pyrite task create --parent <epic-id>` sets a parent reference on the child task, but the parent epic's record doesn't get a corresponding child backlink. Asking "what are this epic's children?" requires a forward query — listing all tasks and filtering for ones whose `parent` field matches.

This works for query but means:
- The parent epic's record is silent about its children (the relationship is one-directional in the data)
- A user reading the parent epic in raw form sees no signal of its scope
- Forward-only-link semantics makes orphan detection harder (a renamed-or-deleted parent leaves child orphans without any signal in the parent)

This is the same `[[wikilink]]` vs `backlinks` design dimension Pyrite already handles for entries via `pyrite backlinks` — but tasks currently don't have analogous infrastructure.

## Proposed solution

Two layers:

**1. On task creation with `--parent`**, append child-id to a `children:` list field on the parent's frontmatter (bidirectional link maintenance, performed atomically with the create).

**2. Add `pyrite task backlinks <id>`** (parallel to `pyrite backlinks` for entries) that surfaces all tasks pointing at the given task as `parent` — useful as a fallback / integrity check.

Optional: add `pyrite task validate` (or include in `pyrite ci`) that checks for orphaned children (parent doesn't exist) and missing-children (parent claims child but child no longer exists).

## Related

- `pyrite backlinks` (existing entry-level command) — same pattern
- `task-status-children-tree-view.md` — uses the children list for fast display

## Effort

M — schema field addition + atomic write on create + validation pass. Not large but touches two surfaces.
