---
id: web-ui-wikilink-rendering-in-lists
type: backlog_item
title: "Web UI: Render wikilinks in entry list card snippets"
kind: feature
status: proposed
priority: medium
effort: S
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

Entry list card snippets display raw wikilink syntax (e.g., `[[some-entry]]`) instead of styled inline text. This looks broken to users and makes snippets harder to scan.

## Solution

Add a lightweight wikilink parser to the snippet rendering pipeline that converts `[[target]]` and `[[target|display]]` syntax into styled inline spans. In list context these should be visually distinct text (not full navigation links) to keep the cards scannable without introducing click-target clutter.
