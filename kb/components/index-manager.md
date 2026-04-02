---
id: index-manager
title: Index Manager
type: component
kind: service
path: pyrite/storage/index.py
owner: core
tags:
- core
- storage
---

Indexes KB entries from markdown files into SQLite for fast search and querying. Handles full re-index, incremental sync, and KB registration. Central coordinator between filesystem (KBRepository) and database (PyriteDB).
