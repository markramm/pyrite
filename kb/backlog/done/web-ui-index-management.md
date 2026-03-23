---
id: web-ui-index-management
type: backlog_item
title: "Web UI: Index rebuild, sync, and embedding management"
kind: feature
status: proposed
priority: high
effort: S
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

Index rebuild, sync, and embedding generation are only available via the CLI. Users cannot check index health, trigger a re-index, or generate embeddings from the web UI, making it impossible to manage the search index without terminal access.

## Solution

Add an index management section to the KB settings page with a rebuild/sync button, index statistics (total entries indexed, last indexed timestamp, embedding coverage), and an embedding generation trigger. Display progress feedback during long-running operations and surface any indexing errors.
