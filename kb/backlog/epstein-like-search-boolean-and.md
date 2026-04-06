---
id: epstein-like-search-boolean-and
type: backlog_item
title: "Epstein LIKE search should support implicit AND for multi-term queries"
kind: feature
status: proposed
priority: medium
effort: S
tags: [epstein-files, search, ux]
---

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
