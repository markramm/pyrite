---
id: entry-type-mismatch-event-vs-timeline-event
title: 'Entry Type Mismatch: event vs timeline_event'
type: backlog_item
tags:
- bug
- mcp
- cascade
kind: bug
status: completed
priority: high
effort: S
---

## Problem

\`kb_create\` produces entries with \`type: event\` while the Cascade extension's pre-existing entries use \`type: timeline_event\`. This means entry_type filtering in search/timeline queries won't catch both populations.

## Root Cause

The MCP \`kb_create\` handler hardcodes \`event\` as the type string, while the Cascade extension registers \`timeline_event\` as its entry type via the plugin system. The \`build_entry\` factory dispatches \`event\` to the core \`EventEntry\` class, not the plugin's \`TimelineEventEntry\`.

## Fix Options

1. **Alias resolution** — Make \`build_entry\` check if a plugin has registered an override for core type names (e.g., cascade registers \`event → timeline_event\`)
2. **KB-level type mapping** — Let \`kb.yaml\` declare type aliases so \`event\` resolves to \`timeline_event\` for that KB
3. **Search-level aliasing** — Make search treat \`event\` and \`timeline_event\` as equivalent when filtering

Option 2 is cleanest — it's configuration, not code convention.

## Verification

- Create an event via MCP in a Cascade KB → should produce \`timeline_event\` type
- Search with \`entry_type=event\` → should return both \`event\` and \`timeline_event\` entries
