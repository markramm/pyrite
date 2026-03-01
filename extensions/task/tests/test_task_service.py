"""Tests for TaskService — operative task operations."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pyrite_task.service import TaskService

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB
from pyrite.storage.repository import KBRepository


@pytest.fixture(scope="class")
def task_env():
    """Create a temp KB environment for task tests (class-scoped for speed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tasks_path = tmpdir / "tasks-kb"
        tasks_path.mkdir()
        (tasks_path / "tasks").mkdir()

        kb_config = KBConfig(
            name="test-tasks",
            path=tasks_path,
            kb_type="task",
            description="Test task KB",
        )
        config = PyriteConfig(
            knowledge_bases=[kb_config],
            settings=Settings(index_path=tmpdir / "index.db"),
        )
        db = PyriteDB(config.settings.index_path)
        db.register_kb(
            name="test-tasks",
            kb_type="task",
            path=str(tasks_path),
            description="Test task KB",
        )

        svc = TaskService(config, db)
        yield {
            "svc": svc,
            "config": config,
            "db": db,
            "kb_config": kb_config,
            "tasks_path": tasks_path,
        }
        db.close()


class TestCreateTask:
    def test_create_task(self, task_env):
        svc = task_env["svc"]
        result = svc.create_task(kb_name="test-tasks", title="Investigate target")
        assert result["created"] is True
        assert result["entry_id"]
        assert result["title"] == "Investigate target"
        assert result["status"] == "open"
        assert result["priority"] == 5

    def test_create_task_with_options(self, task_env):
        svc = task_env["svc"]
        result = svc.create_task(
            kb_name="test-tasks",
            title="Sub task",
            body="Do the thing",
            parent_task="parent-123",
            priority=3,
            assignee="agent:test",
            dependencies=["dep-1"],
        )
        assert result["created"] is True
        assert result["parent_task"] == "parent-123"
        assert result["assignee"] == "agent:test"
        assert result["priority"] == 3

    def test_create_indexes_entry(self, task_env):
        svc = task_env["svc"]
        result = svc.create_task(kb_name="test-tasks", title="Indexed task")
        entry_id = result["entry_id"]

        # Verify it's in the index
        row = task_env["db"]._raw_conn.execute(
            "SELECT * FROM entry WHERE id = ? AND kb_name = ?",
            (entry_id, "test-tasks"),
        ).fetchone()
        assert row is not None
        assert row["title"] == "Indexed task"


class TestUpdateTask:
    def test_update_task(self, task_env):
        svc = task_env["svc"]
        created = svc.create_task(kb_name="test-tasks", title="Update me")
        entry_id = created["entry_id"]

        result = svc.update_task(entry_id, "test-tasks", status="claimed", assignee="agent:a")
        assert result["updated"] is True
        assert result["status"] == "claimed"
        assert result["assignee"] == "agent:a"
        assert result["updates"] == {"status": "claimed", "assignee": "agent:a"}


class TestClaimTask:
    def test_claim_success(self, task_env):
        svc = task_env["svc"]
        created = svc.create_task(kb_name="test-tasks", title="Claim me")
        entry_id = created["entry_id"]

        result = svc.claim_task(entry_id, "test-tasks", "agent:claimer")
        assert result["claimed"] is True
        assert result["assignee"] == "agent:claimer"
        assert result["status"] == "claimed"

    def test_claim_already_claimed(self, task_env):
        svc = task_env["svc"]
        created = svc.create_task(kb_name="test-tasks", title="Already claimed")
        entry_id = created["entry_id"]

        # First claim succeeds
        svc.claim_task(entry_id, "test-tasks", "agent:first")

        # Second claim fails
        result = svc.claim_task(entry_id, "test-tasks", "agent:second")
        assert result["claimed"] is False
        assert "not 'open'" in result["error"]
        assert result["current_status"] == "claimed"

    def test_claim_not_found(self, task_env):
        svc = task_env["svc"]
        result = svc.claim_task("nonexistent", "test-tasks", "agent:x")
        assert result["claimed"] is False
        assert "not found" in result["error"]

    def test_claim_file_failure_rollback(self, task_env):
        svc = task_env["svc"]
        created = svc.create_task(kb_name="test-tasks", title="Rollback test")
        entry_id = created["entry_id"]

        # Make file update fail by patching update_entry
        with patch.object(svc.kb_svc, "update_entry", side_effect=OSError("disk full")):
            result = svc.claim_task(entry_id, "test-tasks", "agent:fail")

        assert result["claimed"] is False
        assert "File update failed" in result["error"]

        # Verify index was rolled back to open
        row = task_env["db"]._raw_conn.execute(
            "SELECT json_extract(metadata, '$.status') as status FROM entry WHERE id = ?",
            (entry_id,),
        ).fetchone()
        assert row["status"] == "open"


class TestDecomposeTask:
    def test_decompose_creates_children(self, task_env):
        svc = task_env["svc"]
        parent = svc.create_task(kb_name="test-tasks", title="Epic task")
        parent_id = parent["entry_id"]

        children = [
            {"title": "Subtask 1"},
            {"title": "Subtask 2", "priority": 3},
            {"title": "Subtask 3", "assignee": "agent:worker"},
        ]
        results = svc.decompose_task(parent_id, "test-tasks", children)

        assert len(results) == 3
        assert all(r["created"] for r in results)

        # Verify parent_task is set on children
        child_tasks = svc.list_tasks(kb_name="test-tasks", parent=parent_id)
        assert len(child_tasks) == 3
        for ct in child_tasks:
            assert ct["parent_task"] == parent_id

    def test_decompose_parent_not_found(self, task_env):
        svc = task_env["svc"]
        with pytest.raises(ValueError, match="not found"):
            svc.decompose_task("nonexistent", "test-tasks", [{"title": "child"}])


class TestCheckpointTask:
    def test_checkpoint_appends_to_body(self, task_env):
        svc = task_env["svc"]
        created = svc.create_task(
            kb_name="test-tasks", title="Checkpoint me", body="Initial body"
        )
        entry_id = created["entry_id"]

        result = svc.checkpoint_task(
            entry_id, "test-tasks", "Found 3 public records"
        )
        assert result["checkpointed"] is True
        assert result["message"] == "Found 3 public records"

        # Verify body was updated
        repo = KBRepository(task_env["kb_config"])
        entry = repo.load(entry_id)
        assert "Initial body" in entry.body
        assert "Found 3 public records" in entry.body
        assert "## Checkpoint" in entry.body

    def test_checkpoint_with_evidence(self, task_env):
        svc = task_env["svc"]
        created = svc.create_task(kb_name="test-tasks", title="Evidence task")
        entry_id = created["entry_id"]

        result = svc.checkpoint_task(
            entry_id,
            "test-tasks",
            "Analyzed connections",
            confidence=0.85,
            partial_evidence=["record-1", "record-2"],
        )
        assert result["confidence"] == 0.85
        assert result["evidence"] == ["record-1", "record-2"]

        # Verify body has evidence
        repo = KBRepository(task_env["kb_config"])
        entry = repo.load(entry_id)
        assert "85%" in entry.body
        assert "`record-1`" in entry.body

    def test_checkpoint_updates_agent_context(self, task_env):
        svc = task_env["svc"]
        created = svc.create_task(kb_name="test-tasks", title="Context task")
        entry_id = created["entry_id"]

        svc.checkpoint_task(
            entry_id, "test-tasks", "Progress", confidence=0.7
        )

        # Verify agent_context updated
        repo = KBRepository(task_env["kb_config"])
        entry = repo.load(entry_id)
        assert entry.agent_context["confidence"] == 0.7
        assert entry.agent_context["last_message"] == "Progress"
        assert "last_checkpoint" in entry.agent_context


class TestRollupParent:
    def test_rollup_all_done(self, task_env):
        svc = task_env["svc"]
        parent = svc.create_task(kb_name="test-tasks", title="Parent task")
        parent_id = parent["entry_id"]

        # Create children
        c1 = svc.create_task(
            kb_name="test-tasks", title="Child 1", parent_task=parent_id
        )
        c2 = svc.create_task(
            kb_name="test-tasks", title="Child 2", parent_task=parent_id
        )

        # Mark parent as in_progress first (need valid transitions)
        svc.update_task(parent_id, "test-tasks", status="claimed")
        svc.update_task(parent_id, "test-tasks", status="in_progress")

        # Complete children through valid transitions
        for cid in [c1["entry_id"], c2["entry_id"]]:
            svc.update_task(cid, "test-tasks", status="claimed")
            svc.update_task(cid, "test-tasks", status="in_progress")
            svc.update_task(cid, "test-tasks", status="done")

        result = svc.rollup_parent(parent_id, "test-tasks")
        assert result is not None
        assert result["rolled_up"] is True
        assert result["children_count"] == 2

    def test_rollup_partial(self, task_env):
        svc = task_env["svc"]
        parent = svc.create_task(kb_name="test-tasks", title="Partial parent")
        parent_id = parent["entry_id"]

        c1 = svc.create_task(
            kb_name="test-tasks", title="Done child", parent_task=parent_id
        )
        svc.create_task(
            kb_name="test-tasks", title="Open child", parent_task=parent_id
        )

        # Complete only one child
        svc.update_task(c1["entry_id"], "test-tasks", status="claimed")
        svc.update_task(c1["entry_id"], "test-tasks", status="in_progress")
        svc.update_task(c1["entry_id"], "test-tasks", status="done")

        result = svc.rollup_parent(parent_id, "test-tasks")
        assert result is None

    def test_rollup_cascading(self, task_env):
        from pyrite_task.plugin import TaskPlugin

        import pyrite.plugins.registry as reg_module
        from pyrite.plugins.context import PluginContext
        from pyrite.plugins.registry import PluginRegistry

        # Register plugin so after_save hooks fire for cascade
        registry = PluginRegistry()
        plugin = TaskPlugin()
        plugin.set_context(
            PluginContext(
                config=task_env["config"],
                db=task_env["db"],
                kb_name="test-tasks",
                kb_type="task",
            )
        )
        registry.register(plugin)
        old_registry = reg_module._registry
        reg_module._registry = registry

        try:
            svc = task_env["svc"]

            # Grandparent → parent → child
            gp = svc.create_task(kb_name="test-tasks", title="Grandparent")
            gp_id = gp["entry_id"]
            p = svc.create_task(
                kb_name="test-tasks", title="Parent", parent_task=gp_id
            )
            p_id = p["entry_id"]
            c = svc.create_task(
                kb_name="test-tasks", title="Child", parent_task=p_id
            )
            c_id = c["entry_id"]

            # Advance grandparent and parent to in_progress
            for tid in [gp_id, p_id]:
                svc.update_task(tid, "test-tasks", status="claimed")
                svc.update_task(tid, "test-tasks", status="in_progress")

            # Complete child
            svc.update_task(c_id, "test-tasks", status="claimed")
            svc.update_task(c_id, "test-tasks", status="in_progress")
            svc.update_task(c_id, "test-tasks", status="done")

            # Rollup parent (should also cascade to grandparent via hook)
            result = svc.rollup_parent(p_id, "test-tasks")
            assert result is not None
            assert result["rolled_up"] is True

            # Grandparent should also be done (via after_save hook on parent)
            repo = KBRepository(task_env["kb_config"])
            gp_entry = repo.load(gp_id)
            assert gp_entry.status == "done"
        finally:
            reg_module._registry = old_registry


class TestListTasks:
    def test_list_all(self, task_env):
        svc = task_env["svc"]
        before = svc.list_tasks(kb_name="test-tasks")
        svc.create_task(kb_name="test-tasks", title="Task A")
        svc.create_task(kb_name="test-tasks", title="Task B")

        tasks = svc.list_tasks(kb_name="test-tasks")
        assert len(tasks) == len(before) + 2

    def test_list_filter_status(self, task_env):
        svc = task_env["svc"]
        before_open = svc.list_tasks(kb_name="test-tasks", status="open")
        svc.create_task(kb_name="test-tasks", title="Open task")
        t2 = svc.create_task(kb_name="test-tasks", title="Claimed task")
        svc.claim_task(t2["entry_id"], "test-tasks", "agent:x")

        open_tasks = svc.list_tasks(kb_name="test-tasks", status="open")
        assert len(open_tasks) == len(before_open) + 1
        titles = [t["title"] for t in open_tasks]
        assert "Open task" in titles

    def test_list_filter_assignee(self, task_env):
        svc = task_env["svc"]
        t1 = svc.create_task(kb_name="test-tasks", title="Assigned")
        svc.claim_task(t1["entry_id"], "test-tasks", "agent:alpha")
        svc.create_task(kb_name="test-tasks", title="Unassigned")

        assigned = svc.list_tasks(kb_name="test-tasks", assignee="agent:alpha")
        assert len(assigned) >= 1
        titles = [t["title"] for t in assigned]
        assert "Assigned" in titles
