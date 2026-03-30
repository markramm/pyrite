---
id: security-audit-trail
type: backlog_item
title: "Security: Append-only hash-chained audit log"
kind: feature
status: proposed
priority: medium
effort: L
tags: [security, audit, integrity]
epic: hosting-security-hardening
links:
- target: hosting-security-hardening
  relation: subtask_of
  kb: pyrite
---

## Problem

No tamper-evident logging exists. Admin users can modify or delete entries without detection. SQLite database is fully mutable. No mechanism to detect post-hoc tampering.

## Fix

Implement an append-only audit log table where each row includes a SHA-256 hash of the previous row (hash chain). Add `pyrite audit verify` command to validate the chain. Consider signing audit entries with a server key.

Files: new `pyrite/services/audit_service.py`, `pyrite/storage/models.py`
