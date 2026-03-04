---
id: sw-adrs-date-field-empty
type: backlog_item
title: "Bug: sw adrs date field always empty"
kind: bug
status: proposed
priority: medium
effort: XS
tags: [cli, software-kb, bug]
---

# Bug: sw adrs date field always empty

## Problem

The `sw adrs` CLI command shows empty dates for all ADRs. The `date` field is read from `r["_meta"].get("date", "")` (the metadata JSON blob), but `date` is a protocol field that gets promoted to a dedicated DB column during indexing and stripped from metadata.

This is the same bug pattern as the `status` field issue that was already fixed for `sw_backlog` and `sw_adrs` (reading from column first, then metadata fallback).

## Fix

In `extensions/software-kb/src/pyrite_software_kb/cli.py`, the ADR date display needs:

```python
# Before:
meta.get("date", "")

# After:
r.get("date") or meta.get("date", "")
```

Apply to both JSON and rich output paths in `sw_adrs`.

## Files

- `extensions/software-kb/src/pyrite_software_kb/cli.py` — `sw_adrs` command
