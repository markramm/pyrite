---
id: security-sqlcipher-option
type: backlog_item
title: "Security: Optional SQLCipher encryption for database at rest"
kind: feature
status: proposed
priority: medium
effort: L
tags: [security, encryption, storage]
epic: hosting-security-hardening
links:
- target: hosting-security-hardening
  relation: subtask_of
  kb: pyrite
---

## Problem

The SQLite database contains all entry content, user accounts, session tokens, and embeddings in plaintext. Anyone with filesystem access can read everything.

## Fix

Add opt-in SQLCipher support: swap `sqlite3` with `pysqlcipher3` when `PYRITE_DB_KEY` env var is set. Requires building pysqlcipher3 with SQLCipher library.

Files: `pyrite/storage/connection.py`, `pyrite/config.py`
