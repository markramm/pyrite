"""WebSocket connection manager for multi-tab awareness."""

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)
        logger.debug("WebSocket connected, total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)
        logger.debug("WebSocket disconnected, total: %d", len(self._connections))

    async def broadcast(self, event: dict[str, Any]):
        """Broadcast an event to all connected clients."""
        if not self._connections:
            return
        message = json.dumps(event)
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


def broadcast_event(event_type: str, **data):
    """Broadcast a WebSocket event, swallowing errors if no event loop is running.

    Safe to call from sync endpoints and CLI contexts where no event loop exists.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast({"type": event_type, **data}))
    except RuntimeError:
        pass  # No event loop (CLI context, sync test, etc.)
