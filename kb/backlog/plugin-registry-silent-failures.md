---
id: plugin-registry-silent-failures
type: backlog_item
title: "Plugin registry swallows errors, returns partial data without indication"
kind: bug
status: proposed
priority: high
effort: S
tags: [plugins, error-handling, reliability]
---

## Problem

Despite the custom exception hierarchy (done in custom-exception-hierarchy), the plugin registry still has broad `except Exception` blocks that silently drop data. In `plugins/registry.py` `_aggregate_dict()` (~line 152-178), if a plugin's `get_entry_types()` or `get_type_metadata()` raises, those types silently disappear from the registry. The caller gets a partial result with no indication anything went wrong.

Same pattern in `server/endpoints/admin.py` (~lines 436-466) where plugin introspection catches and drops errors.

## Impact

- Missing entry types in the registry means entries of that type can't be created or validated
- Admin endpoint returns incomplete plugin info with no `has_errors` flag
- Debugging is difficult because the failure is silent — you only notice when a type is mysteriously absent

## Expected Behavior

`_aggregate_dict()` should either:
1. Return `(result, errors)` tuple so callers can decide how to handle partial data
2. Log at ERROR level (not WARNING) with the specific plugin name and method
3. Include an `errors` field in API responses when plugin loading was partial

## Acceptance Criteria

- Plugin load failures are visible in CLI output (at least on `--verbose`)
- API responses include error metadata when plugins fail partially
- A plugin crashing on `get_entry_types()` produces a clear, actionable error message
