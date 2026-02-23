---
type: adr
title: "Git-Native Markdown Storage"
adr_number: 1
status: accepted
deciders: ["markr"]
date: "2025-06-01"
tags: [architecture, storage]
---

## Context

We needed a storage format for knowledge entries that is human-readable, version-controlled, and portable. Options considered: database-only, JSON files, or markdown with YAML frontmatter.

## Decision

Use markdown files with YAML frontmatter as the source of truth, with SQLite as a derived index for fast queries. Content lives in git; the index is local-only and rebuildable.

## Consequences

- Entries are readable and editable in any text editor
- Full git history for every change (blame, diff, branch)
- Cloning a repo gives you the full KB immediately
- Need to maintain an indexer that parses frontmatter into SQLite
- Two-tier durability: content (git) vs engagement data (SQLite, local-only)
