---
id: odm-layer
title: "ODM Layer: Object-Document Mapper with Backend Abstraction"
type: backlog_item
tags:
- feature
- odm
- storage
- architecture
- core
kind: feature
priority: medium
effort: L
status: planned
links:
- schema-versioning
- postgres-storage-backend
- extension-type-protocols
- bhag-self-configuring-knowledge-infrastructure
- roadmap
---

## Problem

Pyrite stores knowledge as typed documents (markdown + YAML frontmatter) but indexes them through SQLAlchemy ORM on SQLite — a relational database. This creates an impedance mismatch: flexible frontmatter stored as JSON blobs queried via `json_extract()`, separate FTS5 virtual tables, a separate embedding pipeline, and three query systems duct-taped to a relational engine.

Multiple storage backends are planned (SQLite, LanceDB, PostgreSQL). Without an abstraction layer, each backend requires rewriting the service layer.

## Relationship to Schema Versioning

Schema versioning (see [[schema-versioning]]) is **decoupled and ships first** (pre-0.8). It hooks into the existing `KBRepository` load/save paths without requiring the ODM abstraction.

When the ODM lands (post-launch), schema versioning hooks relocate from `KBRepository` into `DocumentManager` — a straightforward move, not a redesign.

See [ADR-0015 addendum](../adrs/0015-odm-layer-and-schema-migration.md) for the rationale.

## Solution

Introduce a Pyrite ODM layer between the service layer (KBService, TaskService, etc.) and storage backends. Modeled on Ming/Allura's ODM from SourceForge, adapted for git-backed file storage.

See [ADR-0015](../adrs/0015-odm-layer-and-schema-migration.md) and [ODM design doc](../designs/odm-layer.md) for full details.

### Phase 1: Define interfaces, wrap existing code (M)

- Define `SearchBackend` protocol (structural, per ADR-0014)
- Implement `SQLiteBackend` wrapping existing `PyriteDB`, `IndexManager`, FTS5, embedding code
- Define `DocumentManager` with load/save/search paths
- Route `KBService` through `DocumentManager` for load/save
- Route search calls through `SearchBackend`
- Relocate schema versioning hooks from `KBRepository` into `DocumentManager`
- **No behavior change** — existing tests pass, same SQLite underneath

### Phase 2: LanceDB backend (L)

- Implement `LanceDBBackend` satisfying `SearchBackend` protocol
- Configuration toggle in pyrite.yaml
- `pyrite index sync` works with LanceDB
- Background embedding pipeline simplified (vectors are native columns)
- Benchmark: hybrid search quality vs current FTS5 + separate semantic

### Phase 3: Postgres backend (M)

- Implement `PostgresBackend` satisfying `SearchBackend` protocol
- Configuration for app_backend (SQLAlchemy) + index_backend (Postgres) if desired
- pgvector for embeddings, tsvector/tsquery for FTS
- Demo site deployment on Postgres
- See [[postgres-storage-backend]]

## Two-Layer Storage Architecture

The ODM formalizes the split between two storage concerns:

**Application state** (relational, needs ACID): Settings, starred entries, API keys, session data. Backend: SQLite or Postgres via SQLAlchemy (existing code, minimal changes).

**Knowledge index** (document-shaped, needs search): Entry metadata, FTS index, vector embeddings, block table, backlink graph. Backend: pluggable — SQLite/FTS5 (current), LanceDB (future), Postgres/pgvector (future).

## Prerequisites

- Service layer enforcement (done, #47)
- Database transaction management (done, #40)
- Unified DB connection model (done, ADR-0013)
- Schema versioning (pre-0.8, decoupled — see [[schema-versioning]])

## Success Criteria

- `SearchBackend` protocol defined and documented
- `SQLiteBackend` wraps existing code behind the protocol (zero behavior change)
- `KBService` routes through `DocumentManager` — direct `PyriteDB` usage eliminated from services
- At least one alternative backend (LanceDB or Postgres) passes the protocol's test suite

## Launch Context

Post-launch (0.9+). The ODM is the right architecture for backend abstraction and resolving the impedance mismatch, but it's the largest architectural change since service layer enforcement — routing 24+ direct `PyriteDB` usages across services, CLI, plugins, and MCP handlers through a new abstraction layer. Not appropriate for the critical path to 0.8 (Announceable Alpha).

Schema versioning ships independently pre-0.8. The ODM ships when backend flexibility is actually needed (Postgres for demo site, LanceDB for improved hybrid search).
