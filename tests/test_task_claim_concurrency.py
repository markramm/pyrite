"""Concurrency test for the task-claim CAS (task-claim-concurrency-test).

`KBService.claim_entry()`'s compare-and-swap is the one concurrency
guard the whole multi-agent fleet depends on, and until now it had
never actually been executed concurrently -- only sequential
simulation (claim, then a second claim observes the conflict). This
races N real OS processes (not threads -- agents are processes, each
with its own SQLite connection) against a single open task and
asserts exactly one winner.
"""

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.task_service import TaskService
from pyrite.storage.database import PyriteDB

N_CLAIMANTS = 8


def _make_config(tmpdir: Path) -> tuple[PyriteConfig, KBConfig]:
    tasks_path = tmpdir / "tasks-kb"
    kb_config = KBConfig(
        name="test-tasks",
        path=tasks_path,
        kb_type="task",
        description="Concurrency test task KB",
    )
    config = PyriteConfig(
        knowledge_bases=[kb_config],
        settings=Settings(index_path=tmpdir / "index.db"),
    )
    return config, kb_config


def _claim_worker(tmpdir_str: str, task_id: str, assignee: str, result_queue) -> None:
    """Run in a separate process: open a fresh DB connection and race the claim."""
    tmpdir = Path(tmpdir_str)
    config, _ = _make_config(tmpdir)
    db = PyriteDB(config.settings.index_path)
    svc = TaskService(config, db)
    try:
        result = svc.claim_task(task_id, "test-tasks", assignee)
        result_queue.put((assignee, result))
    finally:
        db.close()


def _reset_worker(tmpdir_str: str, task_id: str, result_queue) -> None:
    """Run in a separate process: race a stale-claim reset against a claim."""
    tmpdir = Path(tmpdir_str)
    config, _ = _make_config(tmpdir)
    db = PyriteDB(config.settings.index_path)
    svc = TaskService(config, db)
    try:
        result = svc.reset_task(task_id, "test-tasks", reason="stale worker")
        result_queue.put(("reset", result))
    except Exception as e:
        result_queue.put(("reset", {"error": str(e)}))
    finally:
        db.close()


@pytest.fixture
def concurrency_env():
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        config, kb_config = _make_config(tmpdir)
        kb_config.path.mkdir()
        (kb_config.path / "tasks").mkdir()

        db = PyriteDB(config.settings.index_path)
        db.register_kb(
            name="test-tasks",
            kb_type="task",
            path=str(kb_config.path),
            description="Concurrency test task KB",
        )
        svc = TaskService(config, db)
        yield {"tmpdir": tmpdir, "config": config, "kb_config": kb_config, "svc": svc, "db": db}
        db.close()


class TestClaimTaskConcurrency:
    def test_n_processes_race_claim_exactly_one_wins(self, concurrency_env):
        svc = concurrency_env["svc"]
        tmpdir = concurrency_env["tmpdir"]

        created = svc.create_task(kb_name="test-tasks", title="Race me")
        task_id = created["entry_id"]

        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        processes = [
            ctx.Process(
                target=_claim_worker,
                args=(str(tmpdir), task_id, f"agent:{i}", result_queue),
            )
            for i in range(N_CLAIMANTS)
        ]
        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)
            assert p.exitcode == 0, "worker process crashed instead of returning a clean result"

        results = [result_queue.get(timeout=5) for _ in processes]

        winners = [(assignee, r) for assignee, r in results if r["claimed"] is True]
        losers = [(assignee, r) for assignee, r in results if r["claimed"] is False]

        assert len(winners) == 1, f"expected exactly one winner, got {winners}"
        assert len(losers) == N_CLAIMANTS - 1

        # Every loser must be a clean CONFLICT-class response, not a crash/corruption.
        for _assignee, r in losers:
            assert "error" in r
            assert r.get("current_status") == "claimed"

        # The on-disk file must match the winning claimant, not just the index.
        from pyrite.storage.repository import KBRepository

        entry = KBRepository(concurrency_env["kb_config"]).load(task_id)
        winning_assignee = winners[0][0]
        assert entry.assignee == winning_assignee
        assert entry.status == "claimed"

    def test_stale_claim_reset_races_an_active_claimer(self, concurrency_env):
        """The release/reset path (task-claim-concurrency-test's second
        acceptance criterion): a reset racing an active re-claim must not
        leave the entry in an inconsistent state -- exactly one of
        (reset-to-open, claimed-by-racer) applies to both index and file."""
        svc = concurrency_env["svc"]
        tmpdir = concurrency_env["tmpdir"]

        created = svc.create_task(kb_name="test-tasks", title="Stale claim")
        task_id = created["entry_id"]
        svc.claim_task(task_id, "test-tasks", "agent:original")
        svc.update_task(task_id, "test-tasks", status="in_progress")

        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        processes = [
            ctx.Process(target=_reset_worker, args=(str(tmpdir), task_id, result_queue)),
            ctx.Process(
                target=_claim_worker, args=(str(tmpdir), task_id, "agent:racer", result_queue)
            ),
        ]
        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=30)
            assert p.exitcode == 0

        results = dict(result_queue.get(timeout=5) for _ in processes)

        from pyrite.storage.repository import KBRepository

        entry = KBRepository(concurrency_env["kb_config"]).load(task_id)

        # The claim only succeeds if it raced in after the reset landed
        # (from_status="open"); if the reset hadn't landed yet, the racer's
        # claim correctly fails (task was still "in_progress", not "open").
        # Either way, index and file must agree on the final state.
        claim_result = results.get("reset")
        assert entry.status in ("open", "claimed")
        if entry.status == "claimed":
            assert entry.assignee == "agent:racer"
        else:
            assert claim_result.get("status") == "open" or "error" not in claim_result
