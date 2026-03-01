---
type: component
title: "WebSocket Server"
kind: service
path: "pyrite/server/websocket.py"
owner: "markr"
dependencies: ["fastapi", "starlette"]
tags: [server, realtime]
---

# WebSocket Server

The WebSocket server provides real-time push notifications to connected browser tabs so the web frontend can stay in sync when entries are created, updated, or deleted -- either by the same user in another tab or by an external process (CLI, MCP).

## Key Files

| File | Purpose |
|------|---------|
| `pyrite/server/websocket.py` | `ConnectionManager` class and module-level `manager` singleton |
| `pyrite/server/endpoints/entries.py` | Broadcasts events after entry mutations |
| `pyrite/server/endpoints/admin.py` | Broadcasts `kb_synced` after index sync |

## `ConnectionManager` Class

### Methods

- **`connect(ws: WebSocket)`** -- Accepts the WebSocket handshake and adds the connection to the internal `_connections` set.
- **`disconnect(ws: WebSocket)`** -- Removes a connection from the set (uses `discard` for idempotency).
- **`broadcast(event: dict[str, Any])`** -- JSON-serializes the event dict and sends it to every connected client. Dead connections (those that raise on `send_text`) are automatically pruned.

### Properties

- **`connection_count`** -- Number of currently active connections.

### Singleton

The module exports a `manager` instance (`ConnectionManager()`) imported directly by endpoint modules.

## Event Types

All events are JSON objects with a `type` field, `entry_id`, and `kb_name`:

| Event | Trigger |
|-------|---------|
| `entry_created` | After `KBService.create_entry()` succeeds in the entries endpoint |
| `entry_updated` | After `KBService.update_entry()` succeeds in the entries endpoint |
| `entry_deleted` | After `KBService.delete_entry()` succeeds in the entries endpoint |
| `kb_synced` | After `KBService.sync_index()` completes in the admin endpoint |

## Broadcast Pattern

```
Client A (browser tab)  ──ws──>  ConnectionManager
Client B (browser tab)  ──ws──>       |
                                      |
REST endpoint mutates entry ──> broadcast({type, entry_id, kb_name})
                                      |
                              sends JSON to A and B
```

Events are fire-and-forget: the broadcast is awaited but failures on individual connections are silently handled by removing the dead socket.

## Design Notes

- The connection store is a plain `set[WebSocket]`, not a dict keyed by user or session. All connected clients receive all events.
- No authentication or subscription filtering is implemented; the frontend filters events client-side.
- The `broadcast` method handles cleanup of dead connections inline rather than via a background heartbeat.
- Event broadcasting is non-blocking from the endpoint's perspective -- it happens after the DB commit so the response is not delayed.

## Consumers

- **Web frontend** (`web/`) -- connects on page load, listens for events to invalidate caches and refresh entry lists.
- **REST API endpoints** -- import `manager` from `pyrite.server.websocket` and call `broadcast()` after mutations.

## Related

- [[rest-api]] -- endpoints that trigger broadcasts
- [[web-frontend]] -- WebSocket client consumer
- [[kb-service]] -- the service whose operations trigger the events
- [[websocket-multi-tab]] -- backlog item that delivered this component
