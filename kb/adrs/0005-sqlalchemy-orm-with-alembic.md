---
type: adr
title: "SQLAlchemy ORM with Alembic Migrations"
adr_number: 5
status: accepted
deciders: ["markr"]
date: "2025-09-01"
tags: [architecture, storage, database]
---

## Context

The storage layer was using raw SQLite with hand-written SQL. As the schema grew (FTS5, links, tags, plugin tables), migration management became error-prone.

## Decision

Migrate to SQLAlchemy ORM for the data model and add Alembic for schema migrations. Keep the raw connection available for FTS5 queries which SQLAlchemy doesn't handle natively.

## Consequences

- Schema changes are tracked as migration files
- Plugin tables still use raw DDL (IF NOT EXISTS) since they're dynamic
- Dual access pattern: ORM for standard CRUD, raw connection for FTS5 and plugin queries
- MigrationManager handles version tracking with a custom migrations table
