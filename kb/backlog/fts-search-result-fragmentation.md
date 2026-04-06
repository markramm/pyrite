---
id: fts-search-result-fragmentation
type: backlog_item
title: "Epstein FTS search splits single documents into multiple fragments"
kind: bug
status: proposed
priority: medium
effort: M
tags: [epstein-files, search, fts]
---

## Problem

`database/fts_search.sh` in the epstein_files repo splits email content across multiple "result" blocks. For example, searching `"mosquitoes thiel"` for EFTA02645256 rendered as 8 separate fragments instead of one coherent document. Each line of the email appears as a separate search hit.

The LIKE search (`search_epstein.py`) returns the full document correctly for single-document lookups.

The root cause appears to be that quoted-printable encoding (`=AO`, `=n`, `</=pan>`) is not being decoded before FTS indexing, and the FTS index may be splitting on line boundaries.

## Expected Behavior

A single EFTA document should return as a single search result with the matching content shown in context.

## Workaround

Use FTS to find the EFTA number, then use LIKE search with the EFTA ID to get the full content:
```bash
bash database/fts_search.sh "mosquitoes thiel"     # find the doc
python3 database/search_epstein.py "EFTA02645256"   # get full content
```
