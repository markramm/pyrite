---
id: api-module-level-singletons
title: "Replace module-level singletons in api.py with FastAPI app state"
type: backlog_item
tags: [server, testing, reliability]
links:
- target: rest-api
  relation: related
kind: improvement
status: done
priority: high
effort: S
---

# Replace module-level singletons in api.py with FastAPI app state

## Problem

`pyrite/server/api.py` caches `_config`, `_db`, and `_kb_service` as module-level globals. While FastAPI DI rebuilds them if dependencies change, this pattern creates test isolation risk — tests that don't properly reset these globals can interfere with each other, especially under parallel execution (`pytest-xdist`).

## Solution

Move singleton state into FastAPI `app.state` instead of module-level variables. This makes lifecycle explicit (tied to app instance), simplifies test overrides via `app.dependency_overrides`, and eliminates the risk of stale state leaking across tests.

## Files

- `pyrite/server/api.py` — singleton globals and DI functions
- `tests/conftest.py` — test fixture isolation
- `pyrite/server/endpoints/*.py` — any direct imports of globals
