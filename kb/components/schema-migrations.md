---
id: schema-migrations
title: Schema Migrations
type: component
kind: module
path: pyrite/storage/migrations.py
owner: core
dependencies: []
tags:
- core
- storage
---

Sole source of truth for Pyrite's SQLite schema evolution. Tracks applied versions in a `schema_version` table and provides ordered, idempotent forward/rollback migrations, currently at version 16 (through the `edge_endpoint` table for typed relationships).

## Key Methods / Classes

- `Migration` (dataclass) — version, description, up SQL, down SQL
- `MigrationManager.migrate()` — apply all pending migrations in order
- `MigrationManager.rollback()` — revert to a prior version
- `MigrationManager.get_current_version()` — return the highest applied version
- `MigrationManager.get_pending_migrations()` — list unapplied migrations
- `MigrationManager.status()` — human-readable migration state summary

## Consumers

- `ConnectionMixin` — invokes migrations during database init
- Repository classes at startup
- Test fixtures that need a fresh schema

## Related

- [[storage-layer]] — overall persistence architecture
