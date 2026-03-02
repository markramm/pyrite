---
id: web-ui-collection-view-type-safety
title: "Fix Type Safety in Collection Views"
type: backlog_item
tags:
- bug
- web-ui
- typescript
kind: bug
priority: medium
effort: XS
status: done
---

## Problem

The collection view components and routes use unsafe TypeScript casts that bypass type checking, making the code fragile to schema changes and runtime errors:

- `KanbanView.svelte` and `TableView.svelte` cast `EntryResponse as Record<string, unknown>` to access dynamic fields
- `collections/[id]/+page.svelte` accesses `.kanban.group_by`, `.kanban.column_order`, `.gallery.card_fields` on `Record<string, unknown>` without type guards
- `$page.params.id` is typed as `string | undefined` but passed where `string` is expected in `collections/[id]` and `entries/[id]`

## Solution

Add proper type guards and extend TypeScript interfaces to include collection-specific fields:

- Create view configuration types for Kanban, Gallery, and Table with properly typed fields
- Add type guards or discriminated unions for safe view type narrowing
- Use type-safe parameter handling in route components (validate `$page.params` before use)
- Remove unsafe `as Record<string, unknown>` casts

## Success Criteria

- All `Record<string, unknown>` casts removed or replaced with proper types
- View configuration fields properly typed in interfaces
- Route parameters validated on entry
- TypeScript strict mode compatible
