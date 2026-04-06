---
id: search-cli-field-truncation
type: backlog_item
title: "Search CLI truncates title and snippet without ellipsis or indication"
kind: bug
status: proposed
priority: medium
effort: S
tags: [cli, search, ux]
---

## Problem

In `cli/search_commands.py`, search result display silently truncates fields:

- Line ~127: `snippet[:100]` — cuts snippet at 100 chars with no ellipsis
- Line ~131: `title[:40]` — cuts title at 40 chars with no ellipsis

Users can't tell whether they're seeing the full value or a truncated one. For search workflows where you're scanning results to find the right entry, a cut-off title can hide the distinguishing part.

## Expected Behavior

- Truncated fields should show `...` suffix
- JSON output should include the full untruncated value (truncation is a display concern, not a data concern)
- Consider making truncation widths responsive to terminal width

## Acceptance Criteria

- Truncated titles and snippets show `...` when cut
- JSON output (`--format json`) returns full field values
- No change to default display width (40/100 is fine as default)
