"""Concurrency test for the embedding model-cache lock (#207).

`EmbeddingService._get_model()` used to check the model cache under
`_MODEL_CACHE_LOCK`, release the lock, and only then call the (slow,
non-thread-safe) model constructor -- so N concurrent first callers for
a cold model name each built their own copy concurrently. Under real
sentence-transformers/torch that is a segfault or a hang; here we stand
in a stub constructor behind a patchable seam
(``embedding_service._load_model``) so the test needs neither
sentence-transformers nor torch nor the ``embeddings`` marker, and runs
fast and deterministically under ``-n 4``.

Pattern follows tests/test_task_claim_concurrency.py: a start barrier so
the race is real (not sequential-by-scheduling-luck) plus one group
deadline instead of N fixed per-thread timeouts.
"""

from __future__ import annotations

import threading
import time

import pytest

from pyrite.services import embedding_service
from pyrite.services.embedding_service import EmbeddingService

N_CALLERS = 8
_BARRIER_TIMEOUT = 30.0
_GROUP_DEADLINE = 30.0


@pytest.fixture(autouse=True)
def _clear_model_cache():
    """The model cache is process-global; isolate each test from the others."""
    embedding_service._MODEL_CACHE.clear()
    yield
    embedding_service._MODEL_CACHE.clear()


class _StubModel:
    """Stands in for a loaded SentenceTransformer instance."""


def _make_slow_constructor(call_count: list[int], lock: threading.Lock, delay: float = 0.05):
    """A stub model constructor that sleeps briefly, so concurrent callers
    actually overlap in time rather than finishing before the next one starts.
    """

    def _constructor(name: str):
        with lock:
            call_count[0] += 1
        time.sleep(delay)
        return _StubModel()

    return _constructor


def _make_raising_constructor(call_count: list[int], lock: threading.Lock):
    def _constructor(name: str):
        with lock:
            call_count[0] += 1
        raise RuntimeError("simulated model load failure")

    return _constructor


def _join_all(threads: list[threading.Thread], deadline: float = _GROUP_DEADLINE) -> None:
    end = time.monotonic() + deadline
    for t in threads:
        t.join(timeout=max(0.0, end - time.monotonic()))
    still_running = [t.name for t in threads if t.is_alive()]
    assert not still_running, (
        f"{len(still_running)} thread(s) still running after {deadline:.0f}s: {still_running}"
    )


class TestModelLoadIsLocked:
    def test_concurrent_first_callers_load_model_exactly_once(self, monkeypatch):
        """8 threads, 8 fresh EmbeddingService instances, one cold model name:
        the constructor runs exactly once and every caller gets the same object.
        """
        call_count = [0]
        count_lock = threading.Lock()
        monkeypatch.setattr(
            embedding_service,
            "_load_model",
            _make_slow_constructor(call_count, count_lock, delay=0.05),
        )

        services = [EmbeddingService(db=None) for _ in range(N_CALLERS)]
        barrier = threading.Barrier(N_CALLERS, timeout=_BARRIER_TIMEOUT)
        results: list[object] = [None] * N_CALLERS
        errors: list[BaseException] = []
        errors_lock = threading.Lock()

        def _worker(idx: int, svc: EmbeddingService) -> None:
            try:
                barrier.wait()
                results[idx] = svc._get_model()
            except BaseException as e:  # noqa: BLE001
                with errors_lock:
                    errors.append(e)

        threads = [
            threading.Thread(target=_worker, args=(i, svc), name=f"loader-{i}")
            for i, svc in enumerate(services)
        ]
        for t in threads:
            t.start()
        _join_all(threads)

        assert not errors, f"worker thread(s) raised: {errors}"
        assert call_count[0] == 1, (
            f"model constructor called {call_count[0]} times, expected exactly 1"
        )
        assert all(r is not None for r in results), "some caller(s) got no model back"
        first = results[0]
        assert all(r is first for r in results), (
            "callers did not all get the same cached model object"
        )

    def test_failed_load_poisons_nothing_and_retry_succeeds(self, monkeypatch):
        """A raising constructor must not cache a partial/bad result, must not
        leave the lock held, and must not stop a subsequent caller with a
        working constructor from succeeding.
        """
        call_count = [0]
        count_lock = threading.Lock()
        monkeypatch.setattr(
            embedding_service,
            "_load_model",
            _make_raising_constructor(call_count, count_lock),
        )

        services = [EmbeddingService(db=None) for _ in range(N_CALLERS)]
        barrier = threading.Barrier(N_CALLERS, timeout=_BARRIER_TIMEOUT)
        errors: list[BaseException] = []
        errors_lock = threading.Lock()

        def _worker(svc: EmbeddingService) -> None:
            try:
                barrier.wait()
                svc._get_model()
            except BaseException as e:  # noqa: BLE001
                with errors_lock:
                    errors.append(e)

        threads = [
            threading.Thread(target=_worker, args=(svc,), name=f"failer-{i}")
            for i, svc in enumerate(services)
        ]
        for t in threads:
            t.start()
        _join_all(threads)

        # Every caller must have seen the error (none silently got a model).
        assert len(errors) == N_CALLERS
        assert all(isinstance(e, RuntimeError) for e in errors)
        assert embedding_service._MODEL_CACHE == {}, "a failed load must not poison the cache"

        # A following call with a working stub must succeed and use the cache.
        monkeypatch.setattr(
            embedding_service,
            "_load_model",
            lambda name: _StubModel(),
        )
        recovered = EmbeddingService(db=None)._get_model()
        assert isinstance(recovered, _StubModel)
        assert embedding_service._MODEL_CACHE.get("all-MiniLM-L6-v2") is recovered
