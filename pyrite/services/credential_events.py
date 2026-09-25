"""Credential changes, published by the service layer to whoever listens (ADR-0036).

A live-update socket lives no longer than the credential that opened it
(#411). The credential changes here, in ``AuthService`` -- logout, an expired
or evicted session, a role change, a KB grant or revoke -- and the sockets
live in the server layer (``pyrite.server.websocket``), which the service
layer must not import. So ``AuthService`` publishes a ``CredentialChange``
after each such write, and the server subscribes a listener at startup.

Listeners are called synchronously, on whatever thread made the change (a
worker thread for a sync route, the event loop for an ``async def`` route,
the main thread of a CLI process). A listener must be quick and thread-safe
and must not raise; one that raises is logged and skipped, so a broken
listener never fails the write that published the change.

Delivery is in-process only: a change made by another process (a CLI
``pyrite`` command against the same database) reaches no socket. The
per-socket session expiry still bounds a session socket's life in that case.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CredentialChange:
    """One credential change. Exactly one of the two fields is set.

    - ``session_hash``: that session ended (logout, expiry, eviction). Only
      sockets opened with that session are affected.
    - ``user_id``: every credential of that user changed scope (a role
      change, a KB grant or revoke, ``logout_all``).
    """

    user_id: int | None = None
    session_hash: str | None = None


Listener = Callable[[CredentialChange], None]

_listeners: list[Listener] = []
_lock = threading.Lock()


def subscribe(listener: Listener) -> None:
    """Add ``listener``; subscribing one already present is a no-op."""
    with _lock:
        if listener not in _listeners:
            _listeners.append(listener)


def unsubscribe(listener: Listener) -> None:
    with _lock:
        if listener in _listeners:
            _listeners.remove(listener)


def publish(change: CredentialChange) -> None:
    """Tell every listener about ``change``. Never raises."""
    with _lock:
        listeners = list(_listeners)
    for listener in listeners:
        try:
            listener(change)
        except Exception:
            logger.exception("Credential-change listener %r failed", listener)
