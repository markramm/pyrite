---
id: web-ui-entry-creation-fields
type: backlog_item
title: "Web UI: Full metadata fields in entry creation and edit forms"
kind: feature
status: done
priority: high
effort: M
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

The entry creation and edit forms only support title, body, type, and tags. Users cannot set date, importance, status, sources, participants, or custom metadata fields through the web UI, forcing them to edit YAML frontmatter manually or use the CLI.

## Solution

Extend the entry creation and edit forms with a date picker, an importance slider (1-10), a status dropdown populated from known statuses, a sources editor for adding/removing source URLs or references, a participants list editor, and a dynamic key-value editor for custom metadata fields. Validate inputs client-side and submit all fields via the existing API.
