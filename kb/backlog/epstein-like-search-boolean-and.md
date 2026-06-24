---
id: epstein-like-search-boolean-and
title: "Epstein LIKE search should support implicit AND for multi-term queries"
type: backlog_item
tags: [epstein-files, search, ux]
importance: 5
kind: feature
status: deferred
priority: medium
effort: S
rank: 0
---

> **Belongs to the epstein_files repo, not pyrite.** `search_epstein.py` does
> not exist in the pyrite codebase — this is a separate project's tooling. Filed
> here by mistake; deferred in the pyrite backlog. Track and fix in the
> epstein_files repo. (Reclassified 2026-06-24.)

## Problem

`search_epstein.py` LIKE search treats multi-word queries as a single substring match. Searching `"thiel mosquito"` returns zero results because the words appear on different lines of the document. Users expect multi-term queries to mean "documents containing both terms."

FTS search handles this correctly but has its own fragmentation issues (see fts-search-result-fragmentation).

## Solution

When a LIKE query contains multiple space-separated terms, split them and AND them:
```sql
WHERE content LIKE '%thiel%' AND content LIKE '%mosquito%'
```

This matches the behavior users expect from any search tool. Single phrases can still be quoted.

## Workaround

Use FTS search for multi-term queries:
```bash
bash database/fts_search.sh "mosquitoes thiel"
```
