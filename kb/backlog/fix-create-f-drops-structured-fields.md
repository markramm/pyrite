---
id: fix-create-f-drops-structured-fields
type: backlog_item
title: "Bug: pyrite create -f silently drops structured fields"
kind: bug
status: todo
priority: critical
effort: S
tags: [cli, create, bug]
---

## Problem

`-f "actors=ICE,Adelanto"` and `-f "sources=[{json}]"` are silently ignored — the created file has no actors or sources in its frontmatter. No error, no warning. Silent data loss.

## Solution

Either:
1. Make `-f` work for array/object fields (parse JSON values when value starts with `[` or `{`)
2. Add dedicated flags: `--actor "Name"` (repeatable), `--source '{"url":"...","title":"...","tier":1}'` (repeatable)
3. At minimum, warn when a `-f` value is dropped

Option 1 is the simplest fix. Detect JSON-like values and parse them. For comma-separated strings like `actors=ICE,Adelanto`, split on comma into a list.

## Reported By

User testing daily-capture skill with cascade-timeline KB (2026-03-31).
