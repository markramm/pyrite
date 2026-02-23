---
type: component
title: "Storage Layer"
kind: module
path: "pyrite/storage/"
owner: "markr"
dependencies: ["sqlalchemy", "sqlite3"]
tags: [core, storage]
---

The storage layer provides SQLite-based indexing with FTS5 full-text search over git-native markdown content.

## Key Files
- `database.py` — PyriteDB: SQLAlchemy ORM + raw connection for FTS5, creates plugin tables on init
- `index_manager.py` — IndexManager: builds/syncs index from markdown files
- `repository.py` — KBRepository: reads/writes markdown files with frontmatter
- `migrations.py` — MigrationManager: custom schema versioning

## Design
- Two-tier durability: markdown (git) = source of truth, SQLite = derived index
- FTS5 with BM25 ranking for search
- Plugin tables created with IF NOT EXISTS for idempotency
- Raw connection exposed for FTS5 queries that SQLAlchemy can't handle
