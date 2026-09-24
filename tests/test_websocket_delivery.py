"""Events emitted from sync code reach `/ws` sockets (#326, #322).

The entry routes, `POST /api/index/sync` and the IndexWorker's progress
callback are all plain ``def``: FastAPI runs the routes on a worker thread
and the IndexWorker runs its own threads, so none of them has a running event
loop. `broadcast_event` used to look for one, find nothing, and drop the event
silently. It now hands an off-loop event to the loop the server captured at
startup.

**Surface.** One `TestClient` in context per app, so that REST calls, the
startup hook and the sockets share one event loop, as they do under uvicorn.

**No receive timeouts.** A TestClient socket's ``receive`` blocks forever, so
every test broadcasts a *marker* on the loop after the action under test and
reads the socket's messages in order: the event (if it should arrive) comes
first, then the marker. Before the fix the first message is the marker, which
fails the test instead of hanging it. The marker is a ``kb_synced`` (the one
global event, so it reaches scoped sockets too) with a sentinel ``entry_id``
so it cannot be confused with a real ``kb_synced``.
"""

import asyncio
import gc
import tempfile
import threading
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server import websocket as ws_module
from pyrite.server.api import create_app, get_index_worker
from pyrite.server.websocket import broadcast_event, manager
from pyrite.services.auth_service import AuthService
from pyrite.storage.database import PyriteDB

PUBLIC, PRIVATE = "public-kb", "private-kb"
MARKER = {"type": "kb_synced", "entry_id": "__marker__", "kb_name": ""}


def _config(tmp: Path, *, auth: bool) -> PyriteConfig:
    (tmp / PUBLIC).mkdir()
    (tmp / PRIVATE).mkdir()
    return PyriteConfig(
        knowledge_bases=[
            KBConfig(name=PUBLIC, path=tmp / PUBLIC, kb_type="generic", default_role="read"),
            KBConfig(name=PRIVATE, path=tmp / PRIVATE, kb_type="generic", default_role="none"),
        ],
        settings=Settings(
            index_path=tmp / "index.db",
            auth=AuthConfig(enabled=auth, allow_registration=True),
        ),
    )


def _marker(client):
    client.portal.call(manager.broadcast, dict(MARKER))


def _event_then_marker(ws, event):
    """The event arrives, then the marker. Assert the first before reading
    the second: before the fix only the marker comes, and a second
    ``receive`` would block forever."""
    assert ws.receive_json() == event
    assert ws.receive_json() == MARKER


@pytest.fixture
def open_app():
    """The default local install: auth off, every socket unscoped."""
    with tempfile.TemporaryDirectory() as d:
        yield create_app(config=_config(Path(d), auth=False))


@pytest.fixture
def secured():
    """Auth on: an admin (unscoped), a user granted the private KB, a peer."""
    with tempfile.TemporaryDirectory() as d:
        config = _config(Path(d), auth=True)
        app = create_app(config=config)
        tokens = {}
        for name in ("admin-user", "granted", "peer"):
            r = TestClient(app).post(
                "/auth/register", json={"username": name, "password": "password123"}
            )
            assert r.status_code == 200, r.text
            tokens[name] = r.cookies["pyrite_session"]
        db = PyriteDB(config.settings.index_path)
        try:
            auth = AuthService(db, config.settings.auth)
            users = {u["username"]: u["id"] for u in auth.list_users()}
            auth.grant_kb_permission(users["granted"], PRIVATE, "read", users["admin-user"])
        finally:
            db.close()
        yield {"app": app, "tokens": tokens}


def _cookie(token):
    return {"cookie": f"pyrite_session={token}"}


def _create(c, kb, title, headers=None):
    r = c.post("/api/entries", json={"kb": kb, "title": title}, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()["id"]


class TestSyncRoutesDeliver:
    def test_entry_created(self, open_app):
        with TestClient(open_app) as c, c.websocket_connect("/ws") as ws:
            entry_id = _create(c, PUBLIC, "Created note")
            _marker(c)
            _event_then_marker(
                ws, {"type": "entry_created", "entry_id": entry_id, "kb_name": PUBLIC}
            )

    def test_entry_updated(self, open_app):
        with TestClient(open_app) as c:
            entry_id = _create(c, PUBLIC, "Updated note")
            with c.websocket_connect("/ws") as ws:
                r = c.put(f"/api/entries/{entry_id}", json={"kb": PUBLIC, "body": "new body"})
                assert r.status_code == 200, r.text
                _marker(c)
                _event_then_marker(
                    ws, {"type": "entry_updated", "entry_id": entry_id, "kb_name": PUBLIC}
                )

    def test_entry_deleted(self, open_app):
        with TestClient(open_app) as c:
            entry_id = _create(c, PUBLIC, "Deleted note")
            with c.websocket_connect("/ws") as ws:
                r = c.delete(f"/api/entries/{entry_id}", params={"kb": PUBLIC})
                assert r.status_code == 200, r.text
                _marker(c)
                _event_then_marker(
                    ws, {"type": "entry_deleted", "entry_id": entry_id, "kb_name": PUBLIC}
                )

    def test_kb_synced(self, open_app):
        with TestClient(open_app) as c, c.websocket_connect("/ws") as ws:
            r = c.post("/api/index/sync", params={"wait": "true"})
            assert r.status_code == 200, r.text
            _marker(c)
            _event_then_marker(ws, {"type": "kb_synced", "entry_id": "", "kb_name": ""})


class TestScopingHoldsOnTheSyncPath:
    """#218's filter still decides who hears a sync route's event."""

    def test_private_entry_reaches_granted_socket_only(self, secured):
        app, tokens = secured["app"], secured["tokens"]
        with TestClient(app) as c:
            with (
                c.websocket_connect("/ws", headers=_cookie(tokens["granted"])) as granted,
                c.websocket_connect("/ws", headers=_cookie(tokens["peer"])) as peer,
            ):
                entry_id = _create(c, PRIVATE, "Secret", headers=_cookie(tokens["admin-user"]))
                _marker(c)
                _event_then_marker(
                    granted, {"type": "entry_created", "entry_id": entry_id, "kb_name": PRIVATE}
                )
                assert peer.receive_json() == MARKER


def _worker(app):
    return app.dependency_overrides[get_index_worker]()


class TestIndexProgress:
    """IndexWorker threads deliver `index_progress`, scoped by the job's KB."""

    def test_open_install_receives_progress(self, open_app):
        with TestClient(open_app) as c, c.websocket_connect("/ws") as ws:
            r = c.post("/api/index/sync")  # background job, kb_name=None
            assert r.status_code == 200, r.text
            _worker(open_app).wait_for_idle()
            _marker(c)
            first = ws.receive_json()
            assert first["type"] == "index_progress"
            assert first["job_id"] == r.json()["job_id"]

    def test_kb_job_reaches_sockets_that_read_the_kb(self, secured):
        app, tokens = secured["app"], secured["tokens"]
        with TestClient(app) as c:
            with (
                c.websocket_connect("/ws", headers=_cookie(tokens["granted"])) as granted,
                c.websocket_connect("/ws", headers=_cookie(tokens["peer"])) as peer,
            ):
                worker = _worker(app)
                job_id = worker.submit_sync(kb_name=PRIVATE)
                worker.wait_for_idle()
                _marker(c)
                first = granted.receive_json()
                assert first["type"] == "index_progress"
                assert first["job_id"] == job_id
                assert first["kb_name"] == PRIVATE
                assert peer.receive_json() == MARKER

    def test_all_kb_job_reaches_unscoped_sockets_only(self, secured):
        app, tokens = secured["app"], secured["tokens"]
        with TestClient(app) as c:
            with (
                c.websocket_connect("/ws", headers=_cookie(tokens["admin-user"])) as admin,
                c.websocket_connect("/ws", headers=_cookie(tokens["granted"])) as granted,
            ):
                worker = _worker(app)
                job_id = worker.submit_sync(kb_name=None)
                worker.wait_for_idle()
                _marker(c)
                first = admin.receive_json()
                assert first["type"] == "index_progress"
                assert first["job_id"] == job_id
                assert first["kb_name"] is None
                assert granted.receive_json() == MARKER


def _no_unawaited_coroutine(record):
    gc.collect()
    return [w for w in record if "never awaited" in str(w.message)]


class TestLoopLifetime:
    """`manager` is a module global shared by every app in the process."""

    def test_two_apps_in_sequence(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        for root in (a, b):
            app = create_app(config=_config(root, auth=False))
            with TestClient(app) as c, c.websocket_connect("/ws") as ws:
                entry_id = _create(c, PUBLIC, f"Note {root.name}")
                _marker(c)
                assert ws.receive_json()["entry_id"] == entry_id

            # Between apps: the first app's loop is gone. An off-loop event
            # is dropped quietly, with no coroutine left unawaited.
            with warnings.catch_warnings(record=True) as record:
                warnings.simplefilter("always")
                broadcast_event("entry_created", entry_id="x", kb_name=PUBLIC)
                assert _no_unawaited_coroutine(record) == []

    def test_a_closed_captured_loop_is_no_loop(self):
        loop = asyncio.new_event_loop()
        ws_module.bind_loop(loop)
        loop.close()
        try:
            with warnings.catch_warnings(record=True) as record:
                warnings.simplefilter("always")
                broadcast_event("entry_created", entry_id="x", kb_name=PUBLIC)
                errors = []
                t = threading.Thread(
                    target=lambda: _call_capturing(errors),
                )
                t.start()
                t.join()
                assert errors == []
                assert _no_unawaited_coroutine(record) == []
        finally:
            ws_module.unbind_loop(loop)

    def test_no_captured_loop_is_a_quiet_no_op(self):
        # A CLI process never starts the server; nothing to deliver to.
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            broadcast_event("entry_created", entry_id="x", kb_name=PUBLIC)
            assert _no_unawaited_coroutine(record) == []


def _call_capturing(errors):
    try:
        broadcast_event("entry_created", entry_id="x", kb_name=PUBLIC)
    except Exception as e:  # pragma: no cover - the assertion reports it
        errors.append(e)
