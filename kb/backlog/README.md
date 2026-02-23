# Pyrite Backlog

Prioritized list of features, improvements, and bugs for Pyrite.

## Folder Structure

```
kb/backlog/
├── BACKLOG.md          # Prioritized list (source of truth for ordering)
├── README.md           # This file
├── *.md                # Active backlog items (priority work)
├── done/               # Completed items (moved here on completion)
└── future-ideas/       # Lower-priority items not in the current focus
```

## Rules

1. **Active backlog** (`kb/backlog/*.md`): Items we plan to work on. Kept to a manageable size — roughly the top 25-30 priorities.

2. **Done** (`kb/backlog/done/`): Completed items. When finishing a feature, set `status: completed` in frontmatter and move the file here. Update `BACKLOG.md` to reflect the change.

3. **Future ideas** (`kb/backlog/future-ideas/`): Valid ideas that aren't current priorities. Items can be promoted to the active backlog when priorities shift.

4. **BACKLOG.md**: The single prioritized list linking to all items. Always keep this in sync — it's the quick-reference for "what's next."

## Workflow: Completing a Feature

When a backlog item is implemented:

1. Set `status: completed` in the item's YAML frontmatter
2. Move the file to `done/`
3. Update `BACKLOG.md` — move from active list to Completed section
4. If the work revealed new tech debt, cleanup, or follow-on features:
   - Create new backlog item files
   - Add to `future-ideas/` if low priority, or main backlog if high priority
   - Update `BACKLOG.md` with the new items in the right priority position

## Backlog Item Format

Every item uses this frontmatter:

```yaml
---
type: backlog_item
title: "Human-readable title"
kind: feature | improvement | bug
status: proposed | in_progress | completed
priority: high | medium | low
effort: S | M | L | XL
tags: [relevant, tags]
---
```

Body text describes the problem, context, implementation approach, and dependencies.
