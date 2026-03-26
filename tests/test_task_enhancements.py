"""Tests for task service enhancements: auto-unblocking, evidence aggregation, QA query, QA linking."""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.task_service import TaskService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def task_env():
    """Fresh task environment for each test."""
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
        db.register_kb("test-tasks", "task", str(tasks_path), "Test task KB")

        svc = TaskService(config, db)
        yield {"svc": svc, "config": config, "db": db}
        db.close()


def _advance_to_in_progress(svc, task_id, kb_name):
    """Helper: advance a task through the valid state machine to in_progress."""
    svc.claim_task(task_id, kb_name, assignee="test-agent")
    svc.update_task(task_id, kb_name, status="in_progress")


def _advance_to_done(svc, task_id, kb_name):
    """Helper: advance a task through the valid state machine to done."""
    _advance_to_in_progress(svc, task_id, kb_name)
    svc.update_task(task_id, kb_name, status="done")


def _advance_to_blocked(svc, task_id, kb_name):
    """Helper: advance a task through the valid state machine to blocked."""
    _advance_to_in_progress(svc, task_id, kb_name)
    svc.update_task(task_id, kb_name, status="blocked")


class TestDependencyAutoUnblocking:
    def test_unblocks_task_when_dependency_completes(self, task_env):
        svc = task_env["svc"]

        dep = svc.create_task(kb_name="test-tasks", title="Prerequisite")
        dep_id = dep["entry_id"]

        blocked = svc.create_task(
            kb_name="test-tasks", title="Blocked task",
            dependencies=[dep_id],
        )
        blocked_id = blocked["entry_id"]
        _advance_to_blocked(svc, blocked_id, "test-tasks")

        _advance_to_done(svc, dep_id, "test-tasks")

        unblocked = svc.unblock_dependents(dep_id, "test-tasks")
        assert len(unblocked) == 1
        assert unblocked[0]["id"] == blocked_id

    def test_does_not_unblock_if_other_deps_remain(self, task_env):
        svc = task_env["svc"]

        dep1 = svc.create_task(kb_name="test-tasks", title="Dep 1")
        dep2 = svc.create_task(kb_name="test-tasks", title="Dep 2")

        blocked = svc.create_task(
            kb_name="test-tasks", title="Blocked task",
            dependencies=[dep1["entry_id"], dep2["entry_id"]],
        )
        _advance_to_blocked(svc, blocked["entry_id"], "test-tasks")

        _advance_to_done(svc, dep1["entry_id"], "test-tasks")
        unblocked = svc.unblock_dependents(dep1["entry_id"], "test-tasks")

        assert len(unblocked) == 0

    def test_returns_empty_for_no_dependents(self, task_env):
        svc = task_env["svc"]
        task = svc.create_task(kb_name="test-tasks", title="Standalone")
        _advance_to_done(svc, task["entry_id"], "test-tasks")

        unblocked = svc.unblock_dependents(task["entry_id"], "test-tasks")
        assert unblocked == []


class TestEvidenceAggregation:
    def test_aggregates_child_evidence_to_parent(self, task_env):
        svc = task_env["svc"]

        parent = svc.create_task(kb_name="test-tasks", title="Parent task")
        child = svc.create_task(
            kb_name="test-tasks", title="Child task",
            parent=parent["entry_id"],
        )

        # Add evidence to child via checkpoint
        _advance_to_in_progress(svc, child["entry_id"], "test-tasks")
        svc.checkpoint_task(
            child["entry_id"], "test-tasks",
            message="Found evidence",
            partial_evidence=["evidence-entry-1", "evidence-entry-2"],
        )

        # Aggregate up
        result = svc.aggregate_evidence_to_parent(child["entry_id"], "test-tasks")
        assert result is not None
        assert result["evidence_added"] == 2
        assert result["parent_id"] == parent["entry_id"]

    def test_no_aggregation_without_parent(self, task_env):
        svc = task_env["svc"]
        task = svc.create_task(kb_name="test-tasks", title="No parent")

        result = svc.aggregate_evidence_to_parent(task["entry_id"], "test-tasks")
        assert result is None


class TestLinkQAAssessment:
    def test_links_assessment_as_evidence(self, task_env):
        svc = task_env["svc"]

        task = svc.create_task(kb_name="test-tasks", title="QA validation task")
        result = svc.link_qa_assessment(task["entry_id"], "qa-assessment-1", "test-tasks")

        assert result["linked"] is True
        assert result["total_evidence"] == 1

    def test_deduplicates_evidence(self, task_env):
        svc = task_env["svc"]

        task = svc.create_task(kb_name="test-tasks", title="QA task")
        svc.link_qa_assessment(task["entry_id"], "qa-1", "test-tasks")
        result = svc.link_qa_assessment(task["entry_id"], "qa-1", "test-tasks")

        assert result["total_evidence"] == 1  # Not 2

    def test_returns_error_for_missing_task(self, task_env):
        svc = task_env["svc"]
        result = svc.link_qa_assessment("nonexistent", "qa-1", "test-tasks")
        assert result["linked"] is False
