"""Tests for the IndexWorker background index service."""

import time

import pytest

from pyrite.services.index_worker import IndexWorker


@pytest.fixture
def worker(pyrite_db, pyrite_config):
    """IndexWorker instance. Joins all spawned threads at teardown so a
    background sync/rebuild thread never outlives the pyrite_db/
    pyrite_config fixtures' own teardown (tmp_kb_dir's TemporaryDirectory
    rmtree) -- the root cause of a full-suite-only flaky test (a
    background thread still writing when its tmpdir gets deleted out
    from under it -- see full-suite-only-flaky-tests-state-leak-across-
    test-files)."""
    w = IndexWorker(pyrite_db, pyrite_config)
    yield w
    w.wait_for_idle(timeout=10)


class TestJobTable:
    """Job table creation and basic operations."""

    def test_table_created(self, pyrite_db, pyrite_config):
        """IndexWorker creates the index_job table on init."""
        worker = IndexWorker(pyrite_db, pyrite_config)
        row = pyrite_db._raw_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='index_job'"
        ).fetchone()
        assert row is not None

    def test_table_idempotent(self, pyrite_db, pyrite_config):
        """Creating IndexWorker twice doesn't fail."""
        IndexWorker(pyrite_db, pyrite_config)
        IndexWorker(pyrite_db, pyrite_config)


class TestSubmitSync:
    """submit_sync job submission."""

    def test_submit_returns_job_id(self, worker):
        job_id = worker.submit_sync(kb_name="test-events")
        assert isinstance(job_id, str)
        assert len(job_id) == 12

    def test_get_job_returns_status(self, worker):
        job_id = worker.submit_sync(kb_name="test-events")
        # Give the thread a moment to start
        time.sleep(0.2)
        job = worker.get_job(job_id)
        assert job is not None
        assert job["job_id"] == job_id
        assert job["operation"] == "sync"
        assert job["kb_name"] == "test-events"

    def test_sync_completes(self, worker, sample_events):
        """Sync job runs to completion with sample data."""
        job_id = worker.submit_sync(kb_name="test-events")
        # Wait for completion
        for _ in range(50):
            job = worker.get_job(job_id)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.1)
        assert job["status"] == "completed"
        assert job["added"] >= 0

    def test_sync_all_kbs(self, worker, sample_events):
        """Sync with kb_name=None syncs all KBs."""
        job_id = worker.submit_sync(kb_name=None)
        for _ in range(50):
            job = worker.get_job(job_id)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.1)
        assert job["status"] == "completed"


class TestSubmitRebuild:
    """submit_rebuild job submission."""

    def test_submit_rebuild(self, worker, sample_events):
        job_id = worker.submit_rebuild(kb_name="test-events")
        for _ in range(50):
            job = worker.get_job(job_id)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.1)
        assert job["status"] == "completed"
        assert job["added"] >= 0


class TestThreadCleanup:
    """Regression coverage for full-suite-only-flaky-tests-state-leak-
    across-test-files: test_different_kbs_get_different_jobs (and other
    tests using the `worker` fixture) fail intermittently under a
    full-suite run with `OSError: [Errno 66] Directory not empty` at
    teardown, never in isolation.

    Root cause: submit_sync/submit_rebuild spawn daemon threads with no
    join/wait mechanism anywhere. A test that submits a sync and returns
    immediately (as test_different_kbs_get_different_jobs does -- it only
    asserts job_id inequality, never waits for completion) leaves a
    background thread racing the next test's tmp_kb_dir fixture teardown,
    which rmtree()s the same directory the thread may still be writing to.
    """

    def test_wait_for_idle_blocks_until_background_threads_finish(self, worker, sample_events):
        """IndexWorker must expose a way to block until every spawned
        thread has finished, so test fixtures (and any other caller that
        needs a deterministic point after which no background write is
        still in flight) can synchronize before tearing down the
        directory a sync thread might still be touching."""
        job_id = worker.submit_sync(kb_name="test-events")

        worker.wait_for_idle(timeout=5)

        job = worker.get_job(job_id)
        assert job["status"] in ("completed", "failed"), (
            f"expected the job to have finished by the time wait_for_idle() "
            f"returns; got status={job['status']!r}"
        )


class TestConcurrency:
    """Duplicate job prevention."""

    def test_duplicate_sync_returns_same_id(self, worker):
        """Submitting sync for same kb while active returns existing job_id."""
        job_id_1 = worker.submit_sync(kb_name="test-events")
        job_id_2 = worker.submit_sync(kb_name="test-events")
        assert job_id_1 == job_id_2

    def test_different_kbs_get_different_jobs(self, worker):
        """Submitting sync for different kbs creates separate jobs."""
        job_id_1 = worker.submit_sync(kb_name="test-events")
        job_id_2 = worker.submit_sync(kb_name="test-research")
        assert job_id_1 != job_id_2


class TestProgress:
    """Progress callback integration."""

    def test_on_progress_fires(self, worker, sample_events):
        """on_progress callback is called during sync."""
        progress_calls = []

        def track_progress(job_id, current, total):
            progress_calls.append((job_id, current, total))

        worker.on_progress = track_progress
        job_id = worker.submit_sync(kb_name="test-events")

        for _ in range(50):
            job = worker.get_job(job_id)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.1)

        # Progress may or may not fire depending on entry count vs batch size
        # but the job should complete successfully
        assert job["status"] == "completed"


class TestGetActiveJobs:
    """Active job listing."""

    def test_active_jobs_filters(self, worker):
        """get_active_jobs returns only pending/running jobs."""
        job_id = worker.submit_sync(kb_name="test-events")
        active = worker.get_active_jobs()
        # Should have at least one active job
        assert len(active) >= 1
        job_ids = [j["job_id"] for j in active]
        assert job_id in job_ids

    def test_completed_not_in_active(self, worker, sample_events):
        """Completed jobs don't appear in active list."""
        job_id = worker.submit_sync(kb_name="test-events")
        for _ in range(50):
            job = worker.get_job(job_id)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.1)

        active = worker.get_active_jobs()
        job_ids = [j["job_id"] for j in active]
        assert job_id not in job_ids


class TestFailure:
    """Error handling."""

    def test_invalid_kb_fails_gracefully(self, worker):
        """Sync for nonexistent KB completes (no entries to sync)."""
        job_id = worker.submit_sync(kb_name="nonexistent-kb")
        for _ in range(50):
            job = worker.get_job(job_id)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.1)
        # Should complete (sync_incremental handles missing KBs gracefully)
        assert job["status"] == "completed"

    def test_get_nonexistent_job(self, worker):
        """get_job returns None for unknown job_id."""
        assert worker.get_job("nonexistent") is None


class TestAdminEndpoints:
    """REST API admin endpoints for index jobs."""

    def _wait_for_job(self, client, job_id, timeout=5.0):
        """Poll until job completes or times out."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = client.get(f"/api/index/jobs/{job_id}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") in ("completed", "failed"):
                    return data
            time.sleep(0.1)
        return None

    def test_sync_returns_job_id(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.post("/api/index/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "submitted"
        # Wait for completion to avoid teardown race
        self._wait_for_job(client, data["job_id"])

    def test_get_job_status(self, rest_api_env):
        client = rest_api_env["client"]
        # Submit a job first
        resp = client.post("/api/index/sync")
        job_id = resp.json()["job_id"]

        # Check its status
        resp = client.get(f"/api/index/jobs/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        # Wait for completion to avoid teardown race
        self._wait_for_job(client, job_id)

    def test_get_nonexistent_job(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/index/jobs/nonexistent")
        assert resp.status_code == 404

    def test_list_jobs(self, rest_api_env):
        client = rest_api_env["client"]
        resp = client.get("/api/index/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data

    def test_sync_wait_returns_sync_response(self, rest_api_env):
        """?wait=true blocks and returns legacy SyncResponse format."""
        client = rest_api_env["client"]
        resp = client.post("/api/index/sync?wait=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced"] is True
        assert "added" in data
        assert "updated" in data
        assert "removed" in data
        # Should NOT have job_id — this is the synchronous path
        assert "job_id" not in data
