---
id: dynamic-subdirectory-paths
type: backlog_item
title: "Templated Subdirectory Paths for Automatic File Organization"
kind: feature
status: completed
milestone: "0.18"
priority: medium
effort: M
tags: [storage, schema, cli]
---

# Templated Subdirectory Paths for Automatic File Organization

## Problem

Entry types map to static subdirectories (e.g., `backlog_item` → `backlog_item/`). When an entry's status changes (e.g., `proposed` → `completed`), users must manually move the file to `done/`. This is error-prone and breaks the principle that the entry's frontmatter is the source of truth.

## Solution

- `TypeSchema.subdirectory` in kb.yaml now supports `{field}` templates (e.g., `"backlog/{status}"`)
- Templates expand from entry attributes and metadata on save
- File automatically moves when a field value changes
- New `pyrite index reconcile` command for batch-moving misplaced files
- Backward compatible: plain strings work unchanged

## Files modified

- `pyrite/schema/field_schema.py` — `expand_subdirectory_template()`, `TypeSchema.resolve_subdirectory()`
- `pyrite/storage/repository.py` — template expansion in `_infer_subdir()`, recursive `find_file()`
- `pyrite/storage/document_manager.py` — git-aware file movement on save
- `pyrite/cli/index_commands.py` — `reconcile` command

## Success criteria

- Template `{field}` in subdirectory expands from entry attributes/metadata
- Saving an entry with a changed field auto-moves the file
- `pyrite index reconcile <kb> --apply` batch-moves misplaced files
- 22 new tests, all 1823 tests pass
