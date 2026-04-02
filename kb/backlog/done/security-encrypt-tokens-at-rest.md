---
id: security-encrypt-tokens-at-rest
title: "Security: Encrypt GitHub OAuth tokens at rest"
type: backlog_item
tags: [security, encryption, auth]
kind: feature
status: done
priority: high
effort: S
---

## Problem

GitHub OAuth access tokens are stored as plaintext in the `local_user.github_access_token` SQLite column. A seized database exposes all connected users' GitHub tokens.

## Fix

Encrypt tokens using Fernet (symmetric encryption) with a key derived from a server secret (env var `PYRITE_ENCRYPTION_KEY`). Decrypt on read, encrypt on write. Fall back to plaintext if no key configured (with a warning log).

Files: `pyrite/services/auth_service.py`, `pyrite/storage/models.py`
