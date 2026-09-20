"""Concurrency regression tests for #131 — one SQLAlchemy Session shared
across threadpool handlers.

`PyriteDB.__init__` used to create exactly one `sqlalchemy.orm.Session`
(`connection.py`) and keep it for the object's lifetime. The server caches one
`PyriteDB` on `app.state.pyrite_db` and hands it to every request, and ~117 of
the endpoint handlers are plain `def`, which FastAPI runs on anyio's 40-thread
worker pool. `connect_args={"check_same_thread": False}` disables sqlite3's own
cross-thread guard, so instead of a clean `ProgrammingError` the sharing
corrupts SQLAlchemy's result state: the spike measured a 54.6% failure rate
(16 threads x 15 rounds) across four different surface messages from the one
cause:

    114  IndexError: tuple index out of range
     15  InvalidRequestError: This session is provisioning a new connection
      2  SystemError: NULL string with positive size ...
          (and in CI: "This session is in 'prepared' state")

These tests are the spike's A/B arms, kept as regressions:

* `test_concurrent_reads_are_isolated` — Arm A/B: N threads through the real
  `list_entries` + `_get_entry_tags` read path against one `PyriteDB`. 0
  failures required.
* `test_no_pool_timeout_under_handler_concurrency` — the *trap* the spike
  measured: per-thread sessions that are never closed, or a pool smaller than
  the handler concurrency, trade 500s for
  `TimeoutError: QueuePool limit of size 5 overflow 10 reached` (26/40 in the
  spike's intermediate arm).
* `test_engine_pool_covers_handler_concurrency` — criterion 3, asserted rather
  than left to the SQLAlchemy default.
* `test_http_concurrent_reads_return_no_5xx` — criterion 5's shape at the HTTP
  level through `TestClient`.
* `test_verify_api_key_does_no_sync_db_work_on_the_event_loop` — criterion 4.

Threading discipline follows `tests/test_task_claim_concurrency.py`: a start
barrier so the work actually overlaps under a loaded machine, and a single
generous group deadline rather than per-worker wall-clock sleeps, so the file
survives `pytest -n 4`.
"""

from __future__ import annotations

import inspect
import threading
import time
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB

# One deadline for the whole thread group. Threads (not processes) here: the
# bug is in-process session sharing, which processes cannot reproduce.
_GROUP_DEADLINE = 120.0
_BARRIER_TIMEOUT = 60.0

# The spike's arm shape: >=16 threads x >=15 rounds (criterion 2).
N_THREADS = 16
N_ROUNDS = 15

# Errors the shared session produces. Named explicitly so a *different*
# exception (a genuine bug in the read path) is not silently counted as
# "the concurrency bug".
_SHARING_ERRORS = ("IndexError", "InvalidRequestError", "SystemError", "TimeoutError")


def _seed(db: PyriteDB, n: int = 40) -> None:
    """Seed entries with tags, so the read path exercises the join that the
    spike's traceback died in (`base_backend._get_entry_tags`)."""
    db.register_kb(name="concurrency-kb", kb_type="generic", path="/tmp/does-not-exist")
    for i in range(n):
        db.upsert_entry(
            {
                "id": f"entry-{i:03d}",
                "kb_name": "concurrency-kb",
                "entry_type": "note",
                "title": f"Widget note {i}",
                "body": f"Body text about widgets and gadgets number {i}. " * 5,
                "file_path": f"/tmp/does-not-exist/entry-{i:03d}.md",
                "tags": [f"tag-{i % 7}", f"tag-{i % 3}", "common"],
                "sources": [],
                "links": [],
            }
        )


def _run_threads(target, n_threads: int = N_THREADS) -> None:
    """Start `n_threads` on `target(barrier)` and join them under one deadline.

    `target` receives the barrier and is responsible for waiting on it before
    doing contended work. No worker sleeps; the barrier is what makes the
    overlap real when xdist has saturated the cores.
    """
    barrier = threading.Barrier(n_threads, timeout=_BARRIER_TIMEOUT)
    threads = [
        threading.Thread(target=target, args=(barrier,), daemon=True) for _ in range(n_threads)
    ]
    for t in threads:
        t.start()
    end = time.monotonic() + _GROUP_DEADLINE
    for t in threads:
        t.join(timeout=max(0.0, end - time.monotonic()))
    alive = [t.name for t in threads if t.is_alive()]
    assert not alive, f"{len(alive)} worker thread(s) still running after {_GROUP_DEADLINE:.0f}s"


@pytest.fixture
def seeded_db(tmp_path: Path):
    db = PyriteDB(tmp_path / "index.db")
    _seed(db)
    yield db
    db.close()


def test_concurrent_reads_are_isolated(seeded_db: PyriteDB) -> None:
    """Arm B of the spike's A/B: N threads x N rounds of the real read path
    against one `PyriteDB` must produce zero errors.

    On `dev` (one shared `Session`) this fails at roughly the spike's 54.6%.
    """
    errors: list[str] = []
    ok = 0
    lock = threading.Lock()

    def worker(barrier: threading.Barrier) -> None:
        nonlocal ok
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # pragma: no cover - deadline path
            return
        for _ in range(N_ROUNDS):
            try:
                rows = seeded_db.list_entries(kb_name="concurrency-kb", limit=50)
                # Touch the joined tag data: the spike's traceback died inside
                # `_get_entry_tags`, not in the entry select.
                assert all("tags" in r for r in rows)
                with lock:
                    ok += 1
            except Exception as exc:  # noqa: BLE001 - classifying is the point
                with lock:
                    errors.append(f"{type(exc).__name__}: {exc}")

    _run_threads(worker)

    total = ok + len(errors)
    assert total == N_THREADS * N_ROUNDS, f"lost work units: {total}"
    assert not errors, (
        f"{len(errors)}/{total} ({100 * len(errors) / total:.1f}%) concurrent reads failed; "
        f"first 5: {errors[:5]}"
    )


def test_concurrent_reads_and_writes_are_isolated(seeded_db: PyriteDB) -> None:
    """Writers commit while readers read. On a shared session a concurrent
    `commit()` puts it in 'prepared' state for everyone else — the CI face of
    the same bug."""
    errors: list[str] = []
    lock = threading.Lock()

    def worker(barrier: threading.Barrier) -> None:
        idx = threading.get_ident() % 1000
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # pragma: no cover
            return
        for r in range(N_ROUNDS):
            try:
                if r % 4 == 3:
                    seeded_db.upsert_entry(
                        {
                            "id": f"written-{idx}-{r}",
                            "kb_name": "concurrency-kb",
                            "entry_type": "note",
                            "title": f"Written {idx} {r}",
                            "body": "written under concurrency",
                            "file_path": f"/tmp/does-not-exist/written-{idx}-{r}.md",
                            "tags": ["common", f"w-{r}"],
                            "sources": [],
                            "links": [],
                        }
                    )
                else:
                    seeded_db.list_entries(kb_name="concurrency-kb", limit=25)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(f"{type(exc).__name__}: {exc}")

    _run_threads(worker, n_threads=8)

    assert not errors, f"{len(errors)} mixed read/write units failed; first 5: {errors[:5]}"


def test_no_pool_timeout_under_handler_concurrency(seeded_db: PyriteDB) -> None:
    """The measured trap: per-request sessions that leak connections exhaust
    `QueuePool(size=5, max_overflow=10)` long before anyio's 40 threads are
    saturated. 40 concurrent readers must not raise `TimeoutError`."""
    errors: list[str] = []
    lock = threading.Lock()

    def worker(barrier: threading.Barrier) -> None:
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # pragma: no cover
            return
        for _ in range(3):
            try:
                seeded_db.list_entries(kb_name="concurrency-kb", limit=20)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(f"{type(exc).__name__}: {exc}")

    _run_threads(worker, n_threads=40)

    assert not errors, (
        f"{len(errors)} units failed at 40-way concurrency (the anyio threadpool "
        f"width); first 5: {errors[:5]}"
    )


def test_engine_pool_covers_handler_concurrency(seeded_db: PyriteDB) -> None:
    """Criterion 3: the pool must cover the handler concurrency, asserted
    rather than left to SQLAlchemy's default of 5 + 10."""
    from pyrite.storage.connection import HANDLER_CONCURRENCY_LIMIT

    pool = seeded_db.engine.pool
    capacity = pool.size() + pool._max_overflow
    assert capacity >= HANDLER_CONCURRENCY_LIMIT, (
        f"engine pool capacity {capacity} < handler concurrency "
        f"{HANDLER_CONCURRENCY_LIMIT}: a saturated threadpool will raise "
        f"QueuePool timeouts"
    )


def test_request_handles_do_not_share_a_session(seeded_db: PyriteDB) -> None:
    """Criterion 1 for the server's actual mechanism: two concurrent request
    handles must not resolve to the same `Session`.

    A handle shares the engine, pool and backend with its parent `PyriteDB`
    and differs only in its session, so this also pins that the sharing is
    deliberate and the isolation is not.
    """
    seen: list[int] = []
    lock = threading.Lock()

    def worker(barrier: threading.Barrier) -> None:
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # pragma: no cover
            return
        with seeded_db.request_handle() as handle:
            assert handle.engine is seeded_db.engine, "handle must share the engine/pool"
            with lock:
                seen.append(id(handle.session))
            # Hold the handle open until every thread has one, so the ids
            # cannot be recycled between sequential scopes.
            try:
                barrier.wait()
            except threading.BrokenBarrierError:  # pragma: no cover
                return

    _run_threads(worker, n_threads=8)

    assert len(seen) == 8
    assert len(set(seen)) == 8, f"session shared across concurrent request handles: {seen}"


def test_request_handle_reads_are_isolated(seeded_db: PyriteDB) -> None:
    """The server's shape end to end: N concurrent request handles, each doing
    the `list_entries` + `_get_entry_tags` read through its own handle."""
    errors: list[str] = []
    lock = threading.Lock()

    def worker(barrier: threading.Barrier) -> None:
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # pragma: no cover
            return
        for _ in range(N_ROUNDS):
            try:
                with seeded_db.request_handle() as handle:
                    rows = handle.list_entries(kb_name="concurrency-kb", limit=50)
                    assert all("tags" in r for r in rows)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(f"{type(exc).__name__}: {exc}")

    _run_threads(worker)

    assert not errors, f"{len(errors)} request-handle reads failed; first 5: {errors[:5]}"


def test_sessions_are_not_shared_between_scopes(seeded_db: PyriteDB) -> None:
    """Criterion 1, structurally: two concurrent scopes must not receive the
    same `Session` object."""
    seen: list[int] = []
    lock = threading.Lock()

    def worker(barrier: threading.Barrier) -> None:
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # pragma: no cover
            return
        with seeded_db.session_scope() as session:
            with lock:
                seen.append(id(session))
            # Second rendezvous *inside* the scope: every thread holds its own
            # session open until all eight have recorded theirs. Without this
            # the scopes would be sequential and CPython would recycle the id
            # of the previous session, which proves nothing.
            try:
                barrier.wait()
            except threading.BrokenBarrierError:  # pragma: no cover
                return

    _run_threads(worker, n_threads=8)

    assert len(seen) == 8
    # All eight scopes were open simultaneously, so all eight identities must
    # be distinct: no two concurrent scopes may hold the same Session.
    assert len(set(seen)) == 8, f"session objects shared across concurrent scopes: {seen}"


def test_http_concurrent_reads_return_no_5xx(make_client) -> None:
    """Criterion 5's shape at the HTTP level: concurrent reads through the
    real ASGI stack return no 5xx."""
    client, config, db = make_client(kb_name="concurrency-kb")
    _seed(db, n=30)

    paths = [
        "/api/entries?limit=50",
        "/api/entries?limit=20&type=note",
        "/api/tags",
        "/api/search?q=widgets&mode=keyword&limit=20",
        "/api/search?q=gadgets&mode=keyword&limit=20",
    ]

    statuses: list[int] = []
    bodies: list[str] = []
    lock = threading.Lock()
    counter = {"n": 0}

    def worker(barrier: threading.Barrier) -> None:
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # pragma: no cover
            return
        for _ in range(4):
            with lock:
                i = counter["n"]
                counter["n"] += 1
            resp = client.get(paths[i % len(paths)])
            with lock:
                statuses.append(resp.status_code)
                if resp.status_code >= 500:
                    bodies.append(f"{paths[i % len(paths)]} -> {resp.text[:200]}")

    _run_threads(worker, n_threads=8)

    server_errors = [s for s in statuses if s >= 500]
    assert len(statuses) == 32
    assert not server_errors, (
        f"{len(server_errors)}/{len(statuses)} requests returned 5xx under "
        f"concurrency 8; samples: {bodies[:3]}"
    )


def test_verify_api_key_does_no_sync_db_work_on_the_event_loop() -> None:
    """Criterion 4: `verify_api_key` must not call the synchronous
    `AuthService.verify_session` from the event-loop thread.

    Either the dependency became `def` (FastAPI then runs it in the
    threadpool), or the blocking call is explicitly offloaded. Both are
    acceptable; an `async def` that calls the sync path inline is not.
    """
    from pyrite.server.api import verify_api_key

    source = inspect.getsource(verify_api_key)

    if not inspect.iscoroutinefunction(verify_api_key):
        # Plain `def` — FastAPI runs it on the threadpool. Nothing more needed.
        return

    assert "run_in_threadpool" in source or "to_thread" in source, (
        "verify_api_key is async and calls synchronous DB work inline; it must "
        "either be a plain `def` or offload the blocking call"
    )
