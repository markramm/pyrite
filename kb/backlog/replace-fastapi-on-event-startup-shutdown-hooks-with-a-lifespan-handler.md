---
id: replace-fastapi-on-event-startup-shutdown-hooks-with-a-lifespan-handler
title: Replace FastAPI on_event startup/shutdown hooks with a lifespan handler
type: backlog_item
tags:
- quality
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: S
rank: 0
---

## Problem
`create_app` registers startup/shutdown work with the deprecated `@app.on_event` hooks. The count grew by two in #354 (the WebSocket loop binding). FastAPI emits deprecation warnings for each hook, and if the app ever moves to `lifespan=` the hooks are **silently skipped**. That would drop WebSocket event delivery and the startup drains with no failing test. Cold reads on #323 and #354 both flagged it.

## Groom 2026-09-24
**Acceptance**
- `create_app` uses a single `lifespan` async context manager holding every current startup and shutdown step, in the same order. There are no `on_event` calls left in `pyrite/` (grep-pinned by a test).
- `tests/test_websocket_delivery.py`'s loop-lifetime tests and the startup-drain tests still pass unchanged. A new test asserts the loop is bound during a TestClient context and unbound after it.
- The FastAPI `on_event` deprecation warnings are gone from a test run.
**Touches:** `pyrite/server/api.py` and one new test. **Model:** sonnet. **Heavy:** no. **Cold read:** no (mechanical, pinned by existing tests).
**Out of scope:** other deprecation warnings.
