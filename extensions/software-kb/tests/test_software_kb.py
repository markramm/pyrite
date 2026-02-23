"""Tests for the Software KB extension."""

from pyrite_software_kb.entry_types import (
    ADR_STATUSES,
    BACKLOG_EFFORTS,
    BACKLOG_KINDS,
    BACKLOG_PRIORITIES,
    BACKLOG_STATUSES,
    COMPONENT_KINDS,
    DESIGN_DOC_STATUSES,
    RUNBOOK_KINDS,
    STANDARD_CATEGORIES,
    ADREntry,
    BacklogItemEntry,
    ComponentEntry,
    DesignDocEntry,
    RunbookEntry,
    StandardEntry,
)
from pyrite_software_kb.plugin import SoftwareKBPlugin
from pyrite_software_kb.preset import SOFTWARE_KB_PRESET
from pyrite_software_kb.validators import validate_software_kb
from pyrite_software_kb.workflows import (
    ADR_LIFECYCLE,
    BACKLOG_WORKFLOW,
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
        plugin = SoftwareKBPlugin()
        assert plugin.name == "software_kb"

    def test_register_with_registry(self):
        registry = PluginRegistry()
        plugin = SoftwareKBPlugin()
        registry.register(plugin)
        assert "software_kb" in registry.list_plugins()

    def test_entry_types_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        types = registry.get_all_entry_types()
        assert "adr" in types
        assert "design_doc" in types
        assert "standard" in types
        assert "component" in types
        assert "backlog_item" in types
        assert "runbook" in types
        assert types["adr"] is ADREntry
        assert types["design_doc"] is DesignDocEntry

    def test_relationship_types_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        rels = registry.get_all_relationship_types()
        assert "implements" in rels
        assert "supersedes" in rels
        assert "documents" in rels
        assert "depends_on" in rels
        assert "tracks" in rels
        assert rels["implements"]["inverse"] == "implemented_by"
        assert rels["supersedes"]["inverse"] == "superseded_by"

    def test_validators_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        validators = registry.get_all_validators()
        assert validate_software_kb in validators

    def test_cli_commands_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        commands = registry.get_all_cli_commands()
        cmd_names = [name for name, _ in commands]
        assert "sw" in cmd_names

    def test_mcp_read_tools_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        tools = registry.get_all_mcp_tools("read")
        assert "sw_adrs" in tools
        assert "sw_component" in tools
        assert "sw_standards" in tools
        assert "sw_backlog" in tools

    def test_mcp_write_tools_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        tools = registry.get_all_mcp_tools("write")
        assert "sw_create_adr" in tools
        assert "sw_create_backlog_item" in tools
        # Read tools also available at write tier
        assert "sw_adrs" in tools

    def test_mcp_read_tier_no_write_tools(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        tools = registry.get_all_mcp_tools("read")
        assert "sw_create_adr" not in tools
        assert "sw_create_backlog_item" not in tools

    def test_kb_presets_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        presets = registry.get_all_kb_presets()
        assert "software" in presets

    def test_kb_types_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        kb_types = registry.get_all_kb_types()
        assert "software" in kb_types

    def test_workflows_registered(self):
        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())
        workflows = registry.get_all_workflows()
        assert "adr_lifecycle" in workflows
        assert "backlog_workflow" in workflows

    def test_no_db_tables(self):
        plugin = SoftwareKBPlugin()
        assert plugin.get_db_tables() == []


# =========================================================================
# Entry types — ADR
# =========================================================================


class TestADREntry:
    def test_default_values(self):
        entry = ADREntry(id="test", title="Test")
        assert entry.entry_type == "adr"
        assert entry.adr_number == 0
        assert entry.status == "proposed"
        assert entry.deciders == []
        assert entry.date == ""
        assert entry.superseded_by == ""

    def test_to_frontmatter(self):
        entry = ADREntry(
            id="test",
            title="Use PostgreSQL",
            adr_number=1,
            status="accepted",
            deciders=["alice", "bob"],
            date="2026-01-15",
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "adr"
        assert fm["adr_number"] == 1
        assert fm["status"] == "accepted"
        assert fm["deciders"] == ["alice", "bob"]
        assert fm["date"] == "2026-01-15"

    def test_to_frontmatter_omits_defaults(self):
        entry = ADREntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "adr_number" not in fm  # 0 is falsy
        assert "status" not in fm  # proposed is default
        assert "deciders" not in fm
        assert "date" not in fm
        assert "superseded_by" not in fm

    def test_from_frontmatter(self):
        meta = {
            "id": "adr-001",
            "title": "Use PostgreSQL",
            "type": "adr",
            "adr_number": 1,
            "status": "accepted",
            "deciders": ["alice"],
            "date": "2026-01-15",
            "tags": ["database"],
        }
        entry = ADREntry.from_frontmatter(meta, "## Context\n\nWe need a database.")
        assert entry.id == "adr-001"
        assert entry.adr_number == 1
        assert entry.status == "accepted"
        assert entry.deciders == ["alice"]
        assert entry.date == "2026-01-15"
        assert entry.tags == ["database"]
        assert "Context" in entry.body

    def test_from_frontmatter_generates_id(self):
        meta = {"title": "Use Event Sourcing", "type": "adr"}
        entry = ADREntry.from_frontmatter(meta, "")
        assert entry.id == "use-event-sourcing"

    def test_roundtrip_markdown(self):
        entry = ADREntry(
            id="adr-001",
            title="Use PostgreSQL",
            body="## Context\n\nDatabase choice.",
            adr_number=1,
            status="accepted",
            tags=["database"],
        )
        md = entry.to_markdown()
        assert "adr_number: 1" in md
        assert "status: accepted" in md
        assert "Database choice." in md

    def test_superseded_entry(self):
        entry = ADREntry(
            id="adr-001",
            title="Old Decision",
            status="superseded",
            superseded_by="adr-002",
        )
        fm = entry.to_frontmatter()
        assert fm["status"] == "superseded"
        assert fm["superseded_by"] == "adr-002"


# =========================================================================
# Entry types — DesignDoc
# =========================================================================


class TestDesignDocEntry:
    def test_default_values(self):
        entry = DesignDocEntry(id="test", title="Test")
        assert entry.entry_type == "design_doc"
        assert entry.status == "draft"
        assert entry.reviewers == []
        # Inherits from DocumentEntry
        assert entry.date == ""
        assert entry.author == ""
        assert entry.url == ""

    def test_to_frontmatter(self):
        entry = DesignDocEntry(
            id="test",
            title="Auth Design",
            status="review",
            reviewers=["alice", "bob"],
            date="2026-02-01",
            author="charlie",
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "design_doc"
        assert fm["status"] == "review"
        assert fm["reviewers"] == ["alice", "bob"]
        assert fm["date"] == "2026-02-01"
        assert fm["author"] == "charlie"

    def test_to_frontmatter_omits_defaults(self):
        entry = DesignDocEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "status" not in fm  # draft is default
        assert "reviewers" not in fm

    def test_from_frontmatter(self):
        meta = {
            "id": "auth-design",
            "title": "Auth Design",
            "type": "design_doc",
            "status": "approved",
            "reviewers": ["alice"],
            "author": "bob",
            "date": "2026-02-01",
        }
        entry = DesignDocEntry.from_frontmatter(meta, "Design content")
        assert entry.status == "approved"
        assert entry.reviewers == ["alice"]
        assert entry.author == "bob"
        assert entry.date == "2026-02-01"


# =========================================================================
# Entry types — Standard
# =========================================================================


class TestStandardEntry:
    def test_default_values(self):
        entry = StandardEntry(id="test", title="Test")
        assert entry.entry_type == "standard"
        assert entry.category == ""
        assert entry.enforced is False

    def test_to_frontmatter(self):
        entry = StandardEntry(
            id="test", title="Naming Convention", category="coding", enforced=True
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "standard"
        assert fm["category"] == "coding"
        assert fm["enforced"] is True

    def test_to_frontmatter_omits_defaults(self):
        entry = StandardEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "category" not in fm
        assert "enforced" not in fm

    def test_from_frontmatter(self):
        meta = {
            "id": "naming",
            "title": "Naming Convention",
            "type": "standard",
            "category": "coding",
            "enforced": True,
        }
        entry = StandardEntry.from_frontmatter(meta, "Use snake_case")
        assert entry.category == "coding"
        assert entry.enforced is True


# =========================================================================
# Entry types — Component
# =========================================================================


class TestComponentEntry:
    def test_default_values(self):
        entry = ComponentEntry(id="test", title="Test")
        assert entry.entry_type == "component"
        assert entry.kind == ""
        assert entry.path == ""
        assert entry.owner == ""
        assert entry.dependencies == []

    def test_to_frontmatter(self):
        entry = ComponentEntry(
            id="test",
            title="Plugin System",
            kind="module",
            path="pyrite/plugins/",
            owner="alice",
            dependencies=["pyrite.models"],
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "component"
        assert fm["kind"] == "module"
        assert fm["path"] == "pyrite/plugins/"
        assert fm["owner"] == "alice"
        assert fm["dependencies"] == ["pyrite.models"]

    def test_from_frontmatter(self):
        meta = {
            "id": "plugins",
            "title": "Plugin System",
            "type": "component",
            "kind": "module",
            "path": "pyrite/plugins/",
            "dependencies": ["pyrite.models"],
        }
        entry = ComponentEntry.from_frontmatter(meta, "Docs")
        assert entry.kind == "module"
        assert entry.path == "pyrite/plugins/"
        assert entry.dependencies == ["pyrite.models"]


# =========================================================================
# Entry types — BacklogItem
# =========================================================================


class TestBacklogItemEntry:
    def test_default_values(self):
        entry = BacklogItemEntry(id="test", title="Test")
        assert entry.entry_type == "backlog_item"
        assert entry.kind == ""
        assert entry.status == "proposed"
        assert entry.priority == "medium"
        assert entry.assignee == ""
        assert entry.effort == ""

    def test_to_frontmatter(self):
        entry = BacklogItemEntry(
            id="test",
            title="Add caching",
            kind="feature",
            status="accepted",
            priority="high",
            assignee="alice",
            effort="M",
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "backlog_item"
        assert fm["kind"] == "feature"
        assert fm["status"] == "accepted"
        assert fm["priority"] == "high"
        assert fm["assignee"] == "alice"
        assert fm["effort"] == "M"

    def test_to_frontmatter_omits_defaults(self):
        entry = BacklogItemEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "kind" not in fm
        assert "status" not in fm  # proposed is default
        assert "priority" not in fm  # medium is default
        assert "assignee" not in fm
        assert "effort" not in fm

    def test_from_frontmatter(self):
        meta = {
            "id": "caching",
            "title": "Add Caching",
            "type": "backlog_item",
            "kind": "feature",
            "status": "in_progress",
            "priority": "high",
            "effort": "L",
        }
        entry = BacklogItemEntry.from_frontmatter(meta, "Details")
        assert entry.kind == "feature"
        assert entry.status == "in_progress"
        assert entry.priority == "high"
        assert entry.effort == "L"


# =========================================================================
# Entry types — Runbook
# =========================================================================


class TestRunbookEntry:
    def test_default_values(self):
        entry = RunbookEntry(id="test", title="Test")
        assert entry.entry_type == "runbook"
        assert entry.runbook_kind == ""
        assert entry.audience == ""

    def test_to_frontmatter(self):
        entry = RunbookEntry(
            id="test",
            title="Deploy Guide",
            runbook_kind="operations",
            audience="ops-team",
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "runbook"
        assert fm["runbook_kind"] == "operations"
        assert fm["audience"] == "ops-team"

    def test_to_frontmatter_omits_defaults(self):
        entry = RunbookEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "runbook_kind" not in fm
        assert "audience" not in fm

    def test_from_frontmatter(self):
        meta = {
            "id": "deploy",
            "title": "Deploy Guide",
            "type": "runbook",
            "runbook_kind": "operations",
            "audience": "ops-team",
        }
        entry = RunbookEntry.from_frontmatter(meta, "Steps")
        assert entry.runbook_kind == "operations"
        assert entry.audience == "ops-team"


# =========================================================================
# Validators
# =========================================================================


class TestValidators:
    # ADR validators
    def test_adr_valid(self):
        errors = validate_software_kb(
            "adr", {"adr_number": 1, "status": "accepted", "date": "2026-01-01"}, {}
        )
        non_warnings = [e for e in errors if e.get("severity") != "warning"]
        assert non_warnings == []

    def test_adr_invalid_status(self):
        errors = validate_software_kb("adr", {"status": "invalid", "date": "2026-01-01"}, {})
        assert any(e["field"] == "status" for e in errors)

    def test_adr_number_must_be_positive(self):
        errors = validate_software_kb("adr", {"adr_number": -1, "date": "2026-01-01"}, {})
        assert any(e["field"] == "adr_number" for e in errors)

    def test_adr_superseded_requires_link(self):
        errors = validate_software_kb("adr", {"status": "superseded", "date": "2026-01-01"}, {})
        assert any(e["rule"] == "required_when_superseded" for e in errors)

    def test_adr_superseded_with_link_ok(self):
        errors = validate_software_kb(
            "adr",
            {"status": "superseded", "superseded_by": "adr-002", "date": "2026-01-01"},
            {},
        )
        assert not any(e["rule"] == "required_when_superseded" for e in errors)

    def test_adr_date_warning(self):
        errors = validate_software_kb("adr", {"adr_number": 1}, {})
        warnings = [e for e in errors if e.get("severity") == "warning"]
        assert any(e["rule"] == "date_recommended" for e in warnings)

    def test_adr_with_date_no_warning(self):
        errors = validate_software_kb("adr", {"date": "2026-01-01"}, {})
        assert not any(e["rule"] == "date_recommended" for e in errors)

    # Design doc validators
    def test_design_doc_valid(self):
        errors = validate_software_kb("design_doc", {"status": "approved"}, {})
        assert errors == []

    def test_design_doc_invalid_status(self):
        errors = validate_software_kb("design_doc", {"status": "invalid"}, {})
        assert any(e["field"] == "status" for e in errors)

    # Standard validators
    def test_standard_valid(self):
        errors = validate_software_kb("standard", {"category": "coding"}, {})
        assert errors == []

    def test_standard_invalid_category(self):
        errors = validate_software_kb("standard", {"category": "invalid"}, {})
        assert any(e["field"] == "category" for e in errors)

    def test_standard_no_category_ok(self):
        errors = validate_software_kb("standard", {}, {})
        assert errors == []

    # Component validators
    def test_component_valid(self):
        errors = validate_software_kb("component", {"kind": "module", "path": "pyrite/"}, {})
        non_warnings = [e for e in errors if e.get("severity") != "warning"]
        assert non_warnings == []

    def test_component_invalid_kind(self):
        errors = validate_software_kb("component", {"kind": "invalid", "path": "x/"}, {})
        assert any(e["field"] == "kind" for e in errors)

    def test_component_path_warning(self):
        errors = validate_software_kb("component", {"kind": "module"}, {})
        warnings = [e for e in errors if e.get("severity") == "warning"]
        assert any(e["rule"] == "path_recommended" for e in warnings)

    # Backlog validators
    def test_backlog_valid(self):
        errors = validate_software_kb(
            "backlog_item", {"kind": "feature", "status": "proposed", "priority": "high"}, {}
        )
        assert errors == []

    def test_backlog_invalid_kind(self):
        errors = validate_software_kb("backlog_item", {"kind": "invalid"}, {})
        assert any(e["field"] == "kind" for e in errors)

    def test_backlog_invalid_status(self):
        errors = validate_software_kb("backlog_item", {"status": "invalid"}, {})
        assert any(e["field"] == "status" for e in errors)

    def test_backlog_invalid_priority(self):
        errors = validate_software_kb("backlog_item", {"priority": "invalid"}, {})
        assert any(e["field"] == "priority" for e in errors)

    def test_backlog_invalid_effort(self):
        errors = validate_software_kb("backlog_item", {"effort": "XXL"}, {})
        assert any(e["field"] == "effort" for e in errors)

    def test_backlog_valid_effort(self):
        errors = validate_software_kb("backlog_item", {"effort": "XL"}, {})
        assert not any(e["field"] == "effort" for e in errors)

    # Runbook validators
    def test_runbook_valid(self):
        errors = validate_software_kb("runbook", {"runbook_kind": "howto"}, {})
        assert errors == []

    def test_runbook_invalid_kind(self):
        errors = validate_software_kb("runbook", {"runbook_kind": "invalid"}, {})
        assert any(e["field"] == "runbook_kind" for e in errors)

    # Unrelated types
    def test_ignores_unrelated_types(self):
        errors = validate_software_kb("note", {"title": "regular note"}, {})
        assert errors == []


# =========================================================================
# Workflows
# =========================================================================


class TestADRLifecycle:
    def test_states(self):
        assert ADR_LIFECYCLE["states"] == ["proposed", "accepted", "deprecated", "superseded"]
        assert ADR_LIFECYCLE["initial"] == "proposed"
        assert ADR_LIFECYCLE["field"] == "status"

    def test_proposed_to_accepted(self):
        assert can_transition(ADR_LIFECYCLE, "proposed", "accepted", "write")

    def test_accepted_to_deprecated(self):
        assert can_transition(ADR_LIFECYCLE, "accepted", "deprecated", "write")

    def test_accepted_to_superseded(self):
        assert can_transition(ADR_LIFECYCLE, "accepted", "superseded", "write")

    def test_proposed_cannot_skip_to_deprecated(self):
        assert not can_transition(ADR_LIFECYCLE, "proposed", "deprecated", "write")

    def test_no_transition_without_role(self):
        assert not can_transition(ADR_LIFECYCLE, "proposed", "accepted", "")

    def test_allowed_transitions_from_accepted(self):
        allowed = get_allowed_transitions(ADR_LIFECYCLE, "accepted", "write")
        targets = [t["to"] for t in allowed]
        assert "deprecated" in targets
        assert "superseded" in targets


class TestBacklogWorkflow:
    def test_states(self):
        assert "proposed" in BACKLOG_WORKFLOW["states"]
        assert "done" in BACKLOG_WORKFLOW["states"]
        assert "wont_do" in BACKLOG_WORKFLOW["states"]

    def test_happy_path(self):
        assert can_transition(BACKLOG_WORKFLOW, "proposed", "accepted", "write")
        assert can_transition(BACKLOG_WORKFLOW, "accepted", "in_progress", "write")
        assert can_transition(BACKLOG_WORKFLOW, "in_progress", "done", "write")

    def test_wont_do_from_proposed(self):
        assert can_transition(BACKLOG_WORKFLOW, "proposed", "wont_do", "write")

    def test_wont_do_from_accepted(self):
        assert can_transition(BACKLOG_WORKFLOW, "accepted", "wont_do", "write")

    def test_reopen_from_done(self):
        assert can_transition(BACKLOG_WORKFLOW, "done", "accepted", "write")

    def test_wont_do_requires_reason(self):
        assert requires_reason(BACKLOG_WORKFLOW, "proposed", "wont_do")
        assert requires_reason(BACKLOG_WORKFLOW, "accepted", "wont_do")

    def test_reopen_requires_reason(self):
        assert requires_reason(BACKLOG_WORKFLOW, "done", "accepted")

    def test_normal_transitions_no_reason(self):
        assert not requires_reason(BACKLOG_WORKFLOW, "proposed", "accepted")
        assert not requires_reason(BACKLOG_WORKFLOW, "accepted", "in_progress")

    def test_cannot_skip_to_done(self):
        assert not can_transition(BACKLOG_WORKFLOW, "proposed", "done", "write")


# =========================================================================
# Preset
# =========================================================================


class TestPreset:
    def test_preset_structure(self):
        p = SOFTWARE_KB_PRESET
        assert p["name"] == "my-project"
        assert "adr" in p["types"]
        assert "design_doc" in p["types"]
        assert "standard" in p["types"]
        assert "component" in p["types"]
        assert "backlog_item" in p["types"]
        assert "runbook" in p["types"]
        assert p["policies"]["team_owned"] is True
        assert p["policies"]["require_adr_number"] is True
        assert p["validation"]["enforce"] is True

    def test_preset_directories(self):
        dirs = SOFTWARE_KB_PRESET["directories"]
        assert "adrs" in dirs
        assert "designs" in dirs
        assert "standards" in dirs
        assert "components" in dirs
        assert "backlog" in dirs
        assert "runbooks" in dirs

    def test_preset_adr_type(self):
        adr = SOFTWARE_KB_PRESET["types"]["adr"]
        assert "title" in adr["required"]
        assert "adr_number" in adr["optional"]
        assert "status" in adr["optional"]
        assert adr["subdirectory"] == "adrs/"


# =========================================================================
# Enum tuples
# =========================================================================


class TestEnums:
    def test_adr_statuses(self):
        assert "proposed" in ADR_STATUSES
        assert "accepted" in ADR_STATUSES
        assert "deprecated" in ADR_STATUSES
        assert "superseded" in ADR_STATUSES

    def test_design_doc_statuses(self):
        assert "draft" in DESIGN_DOC_STATUSES
        assert "review" in DESIGN_DOC_STATUSES
        assert "approved" in DESIGN_DOC_STATUSES
        assert "implemented" in DESIGN_DOC_STATUSES
        assert "obsolete" in DESIGN_DOC_STATUSES

    def test_standard_categories(self):
        assert "coding" in STANDARD_CATEGORIES
        assert "security" in STANDARD_CATEGORIES
        assert len(STANDARD_CATEGORIES) == 7

    def test_component_kinds(self):
        assert "module" in COMPONENT_KINDS
        assert "service" in COMPONENT_KINDS
        assert len(COMPONENT_KINDS) == 7

    def test_backlog_kinds(self):
        assert "feature" in BACKLOG_KINDS
        assert "bug" in BACKLOG_KINDS
        assert "tech_debt" in BACKLOG_KINDS

    def test_backlog_statuses(self):
        assert "proposed" in BACKLOG_STATUSES
        assert "done" in BACKLOG_STATUSES
        assert "wont_do" in BACKLOG_STATUSES

    def test_backlog_priorities(self):
        assert "critical" in BACKLOG_PRIORITIES
        assert "low" in BACKLOG_PRIORITIES

    def test_backlog_efforts(self):
        assert "XS" in BACKLOG_EFFORTS
        assert "XL" in BACKLOG_EFFORTS
        assert len(BACKLOG_EFFORTS) == 5

    def test_runbook_kinds(self):
        assert "howto" in RUNBOOK_KINDS
        assert "troubleshooting" in RUNBOOK_KINDS
        assert "onboarding" in RUNBOOK_KINDS


# =========================================================================
# Core integration
# =========================================================================


class TestCoreIntegration:
    """Test that the plugin integrates correctly with pyrite core when registered."""

    def test_entry_class_resolution(self):
        """Plugin entry types resolve via get_entry_class when registered."""
        import pyrite.plugins.registry as reg_module
        from pyrite.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())

        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import get_entry_class

            assert get_entry_class("adr") is ADREntry
            assert get_entry_class("design_doc") is DesignDocEntry
            assert get_entry_class("standard") is StandardEntry
            assert get_entry_class("component") is ComponentEntry
            assert get_entry_class("backlog_item") is BacklogItemEntry
            assert get_entry_class("runbook") is RunbookEntry

            # Core types still work
            from pyrite.models.core_types import NoteEntry

            assert get_entry_class("note") is NoteEntry
        finally:
            reg_module._registry = old

    def test_entry_from_frontmatter_resolution(self):
        """Plugin entry types resolve via entry_from_frontmatter when registered."""
        import pyrite.plugins.registry as reg_module
        from pyrite.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())

        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import entry_from_frontmatter

            entry = entry_from_frontmatter(
                {"type": "adr", "title": "Use Postgres", "adr_number": 1}, "Body"
            )
            assert isinstance(entry, ADREntry)
            assert entry.adr_number == 1

            entry = entry_from_frontmatter(
                {"type": "backlog_item", "title": "Fix bug", "kind": "bug"}, "Details"
            )
            assert isinstance(entry, BacklogItemEntry)
            assert entry.kind == "bug"

            entry = entry_from_frontmatter(
                {"type": "component", "title": "Plugin System", "kind": "module"}, "Docs"
            )
            assert isinstance(entry, ComponentEntry)
            assert entry.kind == "module"
        finally:
            reg_module._registry = old

    def test_relationship_types_merged(self):
        """Plugin relationship types merge into schema."""
        import pyrite.plugins.registry as reg_module
        from pyrite.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.register(SoftwareKBPlugin())

        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.schema import get_all_relationship_types, get_inverse_relation

            all_rels = get_all_relationship_types()
            assert "implements" in all_rels
            assert "supersedes" in all_rels
            assert "documents" in all_rels
            assert "depends_on" in all_rels
            assert "tracks" in all_rels

            assert get_inverse_relation("implements") == "implemented_by"
            assert get_inverse_relation("supersedes") == "superseded_by"
            assert get_inverse_relation("depends_on") == "depended_on_by"
            # Core types still work
            assert get_inverse_relation("owns") == "owned_by"
        finally:
            reg_module._registry = old
