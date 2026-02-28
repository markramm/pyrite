"""Tests for the Task extension."""

from pyrite_task.entry_types import TASK_STATUSES, TaskEntry
from pyrite_task.plugin import TaskPlugin
from pyrite_task.preset import TASK_KB_PRESET
from pyrite_task.validators import validate_task
from pyrite_task.workflows import (
    TASK_WORKFLOW,
    can_transition,
    get_allowed_transitions,
    requires_reason,
)

from pyrite.plugins.registry import PluginRegistry

# =========================================================================
# Plugin registration
# =========================================================================


class TestPluginRegistration:
    def test_plugin_has_name(self):
        plugin = TaskPlugin()
        assert plugin.name == "task"

    def test_register_with_registry(self):
        registry = PluginRegistry()
        plugin = TaskPlugin()
        registry.register(plugin)
        assert "task" in registry.list_plugins()

    def test_entry_types_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        types = registry.get_all_entry_types()
        assert "task" in types
        assert types["task"] is TaskEntry

    def test_validators_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        validators = registry.get_all_validators()
        assert validate_task in validators

    def test_cli_commands_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        commands = registry.get_all_cli_commands()
        cmd_names = [name for name, _ in commands]
        assert "task" in cmd_names

    def test_workflows_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        workflows = registry.get_all_workflows()
        assert "task_workflow" in workflows

    def test_mcp_read_tools_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        tools = registry.get_all_mcp_tools("read")
        assert "task_list" in tools
        assert "task_status" in tools

    def test_mcp_write_tools_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        tools = registry.get_all_mcp_tools("write")
        assert "task_create" in tools
        assert "task_update" in tools
        # Read tools also available at write tier
        assert "task_list" in tools

    def test_mcp_read_tier_no_write_tools(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        tools = registry.get_all_mcp_tools("read")
        assert "task_create" not in tools
        assert "task_update" not in tools

    def test_relationship_types_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        rels = registry.get_all_relationship_types()
        assert "subtask_of" in rels
        assert "has_subtask" in rels
        assert "produces" in rels
        assert rels["subtask_of"]["inverse"] == "has_subtask"
        assert rels["produces"]["inverse"] == "produced_by"

    def test_kb_presets_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        presets = registry.get_all_kb_presets()
        assert "task" in presets

    def test_hooks_registered(self):
        registry = PluginRegistry()
        registry.register(TaskPlugin())
        hooks = registry.get_all_hooks()
        assert "before_save" in hooks
        assert "after_save" in hooks
        assert len(hooks["before_save"]) >= 1
        assert len(hooks["after_save"]) >= 1


# =========================================================================
# TaskEntry
# =========================================================================


class TestTaskEntry:
    def test_default_values(self):
        entry = TaskEntry(id="test", title="Test Task")
        assert entry.entry_type == "task"
        assert entry.status == "open"
        assert entry.assignee == ""
        assert entry.parent_task == ""
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
            parent_task="parent-123",
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
        assert fm["parent_task"] == "parent-123"
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
        assert "parent_task" not in fm
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
            "parent_task": "epic-1",
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
        assert entry.parent_task == "epic-1"
        assert entry.dependencies == ["task-000"]
        assert entry.evidence == ["doc-1"]
        assert entry.priority == 2
        assert entry.due_date == "2026-04-01"
        assert entry.agent_context == {"checkpoint": "step3"}
        assert entry.tags == ["api"]
        assert "REST API" in entry.body

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
    """Validator tests — KB-type scoping is handled at the registry level,
    so validate_task always validates when entry_type == "task".
    """

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
        """All task entries are validated regardless of fields present."""
        errors = validate_task("task", {"status": "todo"}, {})
        assert any(e["field"] == "status" for e in errors)


# =========================================================================
# Core integration
# =========================================================================


class TestCoreIntegration:
    def test_entry_class_resolution(self):
        """Plugin entry types resolve via get_entry_class when registered."""
        import pyrite.plugins.registry as reg_module
        from pyrite.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.register(TaskPlugin())

        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import get_entry_class

            assert get_entry_class("task") is TaskEntry
        finally:
            reg_module._registry = old


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
