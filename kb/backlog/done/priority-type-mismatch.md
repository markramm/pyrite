---
id: priority-type-mismatch
type: backlog_item
title: "Bug: priority field type mismatch between entry types and DB column"
kind: bug
status: done
milestone: "0.17"
priority: medium
effort: S
tags: [storage, protocols, bug, type-system]
---

# Bug: priority field type mismatch between entry types and DB column

## Problem

The `priority` DB column is defined as `Integer` in `pyrite/storage/models.py`, but entry types like `BacklogItemEntry` use string values ("high", "medium", "low"). The Prioritizable protocol in ADR-0017 defines priority as an integer (1-5 scale).

This mismatch means:
- String priorities from backlog items are stored in an Integer column (SQLite is lenient, Postgres will reject)
- The dual-source workaround in `sw backlog` checks `r.get("priority") or r["_meta"].get("priority", "medium")` — mixing column (int) and metadata (string)
- Cross-type priority queries ("all high-priority items") won't work consistently

## Options

1. Change DB column to Text — simple, but loses ability to do numeric comparison
2. Map strings to integers during indexing: high=1, medium=3, low=5 — preserves schema intent
3. Change protocol to use string priorities — matches how humans think about priority

## Files

- `pyrite/storage/models.py` — `priority` column type
- `pyrite/storage/index.py` — `_entry_to_dict` priority handling
- `pyrite/models/protocols.py` — Prioritizable protocol definition
