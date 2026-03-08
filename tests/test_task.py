"""Tests for core task entry type, workflow, validators, and hooks."""

import pytest

from pyrite.models.task import (
    TASK_KB_PRESET,
    TASK_STATUSES,
    TASK_WORKFLOW,
    TaskEntry,
    can_transition,
    get_allowed_transitions,
    requires_reason,
)
from pyrite.models.task_validators import validate_task
from pyrite.server.tool_schemas import READ_TOOLS, WRITE_TOOLS


# =========================================================================
# Core registration
# =========================================================================


class TestCoreRegistration:
    def test_entry_type_in_registry(self):
        from pyrite.models.core_types import ENTRY_TYPE_REGISTRY

        assert "task" in ENTRY_TYPE_REGISTRY
        assert ENTRY_TYPE_REGISTRY["task"] is TaskEntry

    def test_get_entry_class_returns_task(self):
        from pyrite.models.core_types import get_entry_class

        assert get_entry_class("task") is TaskEntry

    def test_relationship_types_include_core(self):
        from pyrite.plugins.registry import CORE_RELATIONSHIP_TYPES

        assert "subtask_of" in CORE_RELATIONSHIP_TYPES
        assert "has_subtask" in CORE_RELATIONSHIP_TYPES
        assert "produces" in CORE_RELATIONSHIP_TYPES
        assert CORE_RELATIONSHIP_TYPES["subtask_of"]["inverse"] == "has_subtask"
        assert CORE_RELATIONSHIP_TYPES["produces"]["inverse"] == "produced_by"

    def test_kb_presets_include_task(self):
        from pyrite.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        presets = registry.get_all_kb_presets()
        assert "task" in presets

    def test_core_hooks_registered(self):
        from pyrite.services.kb_service import _CORE_HOOKS

        assert "before_save" in _CORE_HOOKS
        assert "after_save" in _CORE_HOOKS
        assert len(_CORE_HOOKS["before_save"]) >= 1
        assert len(_CORE_HOOKS["after_save"]) >= 1


# =========================================================================
# TaskEntry
# =========================================================================


class TestTaskEntry:
    def test_default_values(self):
        entry = TaskEntry(id="test", title="Test Task")
        assert entry.entry_type == "task"
        assert entry.status == "open"
        assert entry.assignee == ""
        assert entry.parent == ""
        assert entry.dependencies == []
        assert entry.evidence == []
        assert entry.priority == 5
        assert entry.due_date == ""
        assert entry.agent_context == {}

    def test_to_frontmatter(self):
        entry = TaskEntry(
            id="test",
            title="Implement Feature",
            status="in_progress",
            assignee="agent:claude-code-7a3f",
            parent="parent-123",
            dependencies=["dep-1", "dep-2"],
            evidence=["doc-1"],
            priority=3,
            due_date="2026-03-01",
            agent_context={"confidence": 0.9},
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "task"
        assert fm["status"] == "in_progress"
        assert fm["assignee"] == "agent:claude-code-7a3f"
        assert fm["parent"] == "parent-123"
        assert fm["dependencies"] == ["dep-1", "dep-2"]
        assert fm["evidence"] == ["doc-1"]
        assert fm["priority"] == 3
        assert fm["due_date"] == "2026-03-01"
        assert fm["agent_context"] == {"confidence": 0.9}

    def test_to_frontmatter_omits_defaults(self):
        entry = TaskEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "status" not in fm  # open is default
        assert "assignee" not in fm
        assert "parent" not in fm
        assert "dependencies" not in fm
        assert "evidence" not in fm
        assert "priority" not in fm  # 5 is default
        assert "due_date" not in fm
        assert "agent_context" not in fm

    def test_from_frontmatter(self):
        meta = {
            "id": "task-001",
            "title": "Build API",
            "type": "task",
            "status": "claimed",
            "assignee": "agent:test",
            "parent": "epic-1",
            "dependencies": ["task-000"],
            "evidence": ["doc-1"],
            "priority": 2,
            "due_date": "2026-04-01",
            "agent_context": {"checkpoint": "step3"},
            "tags": ["api"],
        }
        entry = TaskEntry.from_frontmatter(meta, "Build the REST API.")
        assert entry.id == "task-001"
        assert entry.status == "claimed"
        assert entry.assignee == "agent:test"
        assert entry.parent == "epic-1"
        assert entry.dependencies == ["task-000"]
        assert entry.evidence == ["doc-1"]
        assert entry.priority == 2
        assert entry.due_date == "2026-04-01"
        assert entry.agent_context == {"checkpoint": "step3"}
        assert entry.tags == ["api"]
        assert "REST API" in entry.body

    def test_from_frontmatter_legacy_parent_task(self):
        """Legacy parent_task field should be accepted."""
        meta = {
            "id": "task-002",
            "title": "Legacy task",
            "type": "task",
            "parent_task": "old-parent",
        }
        entry = TaskEntry.from_frontmatter(meta, "")
        assert entry.parent == "old-parent"

    def test_roundtrip_markdown(self):
        entry = TaskEntry(
            id="task-001",
            title="Build API",
            body="## Description\n\nBuild the API.",
            status="in_progress",
            priority=3,
            tags=["api"],
        )
        md = entry.to_markdown()
        assert "status: in_progress" in md
        assert "priority: 3" in md
        assert "Build the API." in md


# =========================================================================
# Workflows
# =========================================================================


class TestTaskWorkflow:
    def test_states(self):
        assert TASK_WORKFLOW["states"] == [
            "open", "claimed", "in_progress", "blocked", "review", "done", "failed"
        ]
        assert TASK_WORKFLOW["initial"] == "open"
        assert TASK_WORKFLOW["field"] == "status"

    def test_happy_path(self):
        assert can_transition(TASK_WORKFLOW, "open", "claimed", "write")
        assert can_transition(TASK_WORKFLOW, "claimed", "in_progress", "write")
        assert can_transition(TASK_WORKFLOW, "in_progress", "done", "write")

    def test_blocked_resume(self):
        assert can_transition(TASK_WORKFLOW, "in_progress", "blocked", "write")
        assert can_transition(TASK_WORKFLOW, "blocked", "in_progress", "write")

    def test_review_done(self):
        assert can_transition(TASK_WORKFLOW, "in_progress", "review", "write")
        assert can_transition(TASK_WORKFLOW, "review", "done", "write")

    def test_review_back_to_in_progress(self):
        assert can_transition(TASK_WORKFLOW, "review", "in_progress", "write")

    def test_failed_to_open_requires_reason(self):
        assert can_transition(TASK_WORKFLOW, "in_progress", "failed", "write")
        assert can_transition(TASK_WORKFLOW, "failed", "open", "write")
        assert requires_reason(TASK_WORKFLOW, "failed", "open")

    def test_cannot_skip_states(self):
        assert not can_transition(TASK_WORKFLOW, "open", "done", "write")
        assert not can_transition(TASK_WORKFLOW, "open", "in_progress", "write")
        assert not can_transition(TASK_WORKFLOW, "claimed", "done", "write")

    def test_no_transition_without_role(self):
        assert not can_transition(TASK_WORKFLOW, "open", "claimed", "")

    def test_allowed_transitions_from_in_progress(self):
        allowed = get_allowed_transitions(TASK_WORKFLOW, "in_progress", "write")
        targets = [t["to"] for t in allowed]
        assert "blocked" in targets
        assert "review" in targets
        assert "done" in targets
        assert "failed" in targets


# =========================================================================
# Validators
# =========================================================================


class TestValidators:
    def test_valid_task(self):
        errors = validate_task("task", {"status": "open", "priority": 5}, {})
        assert errors == []

    def test_invalid_status(self):
        errors = validate_task("task", {"status": "invalid"}, {})
        assert any(e["field"] == "status" for e in errors)

    def test_invalid_priority_high(self):
        errors = validate_task("task", {"priority": 11}, {})
        assert any(e["field"] == "priority" for e in errors)

    def test_invalid_priority_low(self):
        errors = validate_task("task", {"priority": 0}, {})
        assert any(e["field"] == "priority" for e in errors)

    def test_non_task_ignored(self):
        errors = validate_task("note", {"status": "invalid"}, {})
        assert errors == []

    def test_validates_any_task_entry(self):
        errors = validate_task("task", {"status": "todo"}, {})
        assert any(e["field"] == "status" for e in errors)

    def test_parent_field_validated(self):
        errors = validate_task("task", {"parent": 123}, {})
        assert any(e["field"] == "parent" for e in errors)


# =========================================================================
# Hooks
# =========================================================================


class TestHooks:
    def test_before_save_validates_transition_with_old_status(self):
        from unittest.mock import MagicMock

        from pyrite.plugins.context import PluginContext
        from pyrite.services.kb_service import _task_validate_transition

        entry = TaskEntry(id="t1", title="Test", status="done")
        ctx = PluginContext(
            config=MagicMock(),
            db=MagicMock(),
            kb_name="test",
            operation="update",
            kb_type="task",
            extra={"old_status": "open"},
        )
        # open → done is not a valid transition
        with pytest.raises(ValueError, match="Invalid task transition"):
            _task_validate_transition(entry, ctx)

    def test_before_save_allows_valid_transition(self):
        from unittest.mock import MagicMock

        from pyrite.plugins.context import PluginContext
        from pyrite.services.kb_service import _task_validate_transition

        entry = TaskEntry(id="t1", title="Test", status="claimed")
        ctx = PluginContext(
            config=MagicMock(),
            db=MagicMock(),
            kb_name="test",
            operation="update",
            kb_type="task",
            extra={"old_status": "open"},
        )
        result = _task_validate_transition(entry, ctx)
        assert result.status == "claimed"

    def test_before_save_ignores_non_update(self):
        from unittest.mock import MagicMock

        from pyrite.plugins.context import PluginContext
        from pyrite.services.kb_service import _task_validate_transition

        entry = TaskEntry(id="t1", title="Test", status="done")
        ctx = PluginContext(
            config=MagicMock(),
            db=MagicMock(),
            kb_name="test",
            operation="create",
            kb_type="task",
            extra={"old_status": "open"},
        )
        result = _task_validate_transition(entry, ctx)
        assert result.status == "done"


# =========================================================================
# MCP tool schemas
# =========================================================================


class TestMCPToolSchemas:
    def test_task_list_in_read_tools(self):
        assert "task_list" in READ_TOOLS
        assert "task_status" in READ_TOOLS

    def test_task_write_tools_present(self):
        assert "task_create" in WRITE_TOOLS
        assert "task_update" in WRITE_TOOLS
        assert "task_claim" in WRITE_TOOLS
        assert "task_decompose" in WRITE_TOOLS
        assert "task_checkpoint" in WRITE_TOOLS

    def test_task_create_requires_kb_name_and_title(self):
        schema = WRITE_TOOLS["task_create"]["inputSchema"]
        assert "kb_name" in schema["required"]
        assert "title" in schema["required"]

    def test_task_claim_requires_all_fields(self):
        schema = WRITE_TOOLS["task_claim"]["inputSchema"]
        assert set(schema["required"]) == {"task_id", "kb_name", "assignee"}

    def test_task_decompose_schema(self):
        schema = WRITE_TOOLS["task_decompose"]["inputSchema"]
        assert "parent_id" in schema["required"]
        assert "children" in schema["required"]


# =========================================================================
# Preset
# =========================================================================


class TestPreset:
    def test_preset_structure(self):
        p = TASK_KB_PRESET
        assert p["name"] == "task-board"
        assert "task" in p["types"]
        assert p["policies"]["enforce_workflow"] is True
        assert p["validation"]["enforce"] is True

    def test_preset_task_type(self):
        task_type = TASK_KB_PRESET["types"]["task"]
        assert "title" in task_type["required"]
        assert "status" in task_type["optional"]
        assert "priority" in task_type["optional"]
        assert task_type["subdirectory"] == "tasks/"

    def test_preset_directories(self):
        assert "tasks" in TASK_KB_PRESET["directories"]


# =========================================================================
# Enums
# =========================================================================


class TestEnums:
    def test_task_statuses(self):
        assert "open" in TASK_STATUSES
        assert "claimed" in TASK_STATUSES
        assert "in_progress" in TASK_STATUSES
        assert "blocked" in TASK_STATUSES
        assert "review" in TASK_STATUSES
        assert "done" in TASK_STATUSES
        assert "failed" in TASK_STATUSES
        assert len(TASK_STATUSES) == 7
