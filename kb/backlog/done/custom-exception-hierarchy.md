---
type: backlog_item
title: "Add Custom Exception Hierarchy and Fix Silent Swallowing"
kind: improvement
status: done
priority: high
effort: M
tags: [error-handling, dx]
---

Two related problems:

**1. No custom exceptions** — the codebase uses generic `ValueError` everywhere. A hierarchy like `PyriteError > EntryNotFoundError, ValidationError, PluginError, StorageError` would make error handling precise and let callers catch specific failures.

**2. Broad `except Exception` with silent `pass`** — ~74 instances across the codebase. The worst offenders:
- `schema.py` validation: three nested try/except with bare `pass` — makes plugin validator debugging impossible
- `database.py` `_create_plugin_tables()`: swallows table creation failures silently, causing cryptic SQL errors later
- `core_types.py` `get_entry_class()`: silently falls back to GenericEntry if registry is broken
- `services/kb_service.py` `_run_hooks()`: returns original entry on exception instead of propagating, defeating before-hooks that should abort operations

Fix: replace bare `pass` with `logger.warning()` at minimum; use custom exceptions where callers need to distinguish error types.
