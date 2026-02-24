---
type: backlog_item
title: "WebSocket Multi-Tab Awareness"
kind: feature
status: done
priority: medium
effort: M
tags: [web, api, phase-3]
---

Real-time change notifications across browser tabs:

**Backend:**
- `WS /ws` endpoint for change notifications
- `ConnectionManager` class in `websocket.py` — tracks sessions, broadcasts events
- CRUD endpoints call `manager.notify_change()` after mutations
- Events: entry created, updated, deleted, KB synced

**Frontend:**
- `websocket.ts` client — connects on app init, auto-reconnect with backoff
- Dispatches events to Svelte stores
- Toast notifications when other tabs modify entries
- Stores auto-refresh stale data

Not collaborative editing — just awareness notifications for the same user across tabs.
