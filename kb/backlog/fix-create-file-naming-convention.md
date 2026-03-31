---
id: fix-create-file-naming-convention
type: backlog_item
title: "pyrite create should respect KB file naming conventions"
kind: feature
status: todo
priority: high
effort: M
tags: [cli, create, ux]
---

## Problem

`pyrite create -k cascade-timeline -t event --date 2026-03-30 --title "Event Title"` creates the file as `events/event-title.md` inside the KB directory. But the cascade-timeline KB stores files as `YYYY-MM-DD--event-slug.md` in the KB root (no subdirectory). This means created events don't match the 4,500+ existing files.

## Solution

`pyrite create` should:
- Use the KB's existing naming convention (detect from existing files, or allow config)
- For event-type KBs, default to `{date}--{slug}.md` in the KB root
- Respect a `file_pattern` config option in `kb.yaml` if one exists

Example `kb.yaml`:
```yaml
file_pattern: "{date}--{slug}.md"
file_directory: ""  # root, no subdirectory
```

## Reported By

User testing daily-capture skill with cascade-timeline KB (2026-03-31).
