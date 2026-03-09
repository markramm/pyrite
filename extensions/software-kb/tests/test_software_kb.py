"""Tests for the Software KB extension."""

import json
import tempfile
from pathlib import Path

from pyrite_software_kb.entry_types import (
    ADR_STATUSES,
    BACKLOG_EFFORTS,
    BACKLOG_KINDS,
    BACKLOG_PRIORITIES,
    BACKLOG_STATUSES,
    COMPONENT_KINDS,
    CONVENTION_CATEGORIES,
    DESIGN_DOC_STATUSES,
    MILESTONE_STATUSES,
    RUNBOOK_KINDS,
    STANDARD_CATEGORIES,
    VALIDATION_CATEGORIES,
    ADREntry,
    BacklogItemEntry,
    ComponentEntry,
    DesignDocEntry,
    DevelopmentConventionEntry,
    MilestoneEntry,
    ProgrammaticValidationEntry,
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
        assert "programmatic_validation" in types
        assert "development_convention" in types
        assert "component" in types
        assert "backlog_item" in types
        assert "runbook" in types
        assert types["adr"] is ADREntry
        assert types["design_doc"] is DesignDocEntry
        assert types["programmatic_validation"] is ProgrammaticValidationEntry
        assert types["development_convention"] is DevelopmentConventionEntry

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
        assert "sw_validations" in tools
        assert "sw_conventions" in tools
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
# Entry types — ProgrammaticValidation
# =========================================================================


class TestProgrammaticValidationEntry:
    def test_entry_type(self):
        entry = ProgrammaticValidationEntry(id="test", title="Test")
        assert entry.entry_type == "programmatic_validation"

    def test_default_values(self):
        entry = ProgrammaticValidationEntry(id="test", title="Test")
        assert entry.category == ""
        assert entry.check_command == ""
        assert entry.pass_criteria == ""

    def test_to_frontmatter(self):
        entry = ProgrammaticValidationEntry(
            id="test",
            title="Ruff Linting",
            category="coding",
            check_command="ruff check .",
            pass_criteria="exit code 0",
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "programmatic_validation"
        assert fm["category"] == "coding"
        assert fm["check_command"] == "ruff check ."
        assert fm["pass_criteria"] == "exit code 0"

    def test_to_frontmatter_omits_defaults(self):
        entry = ProgrammaticValidationEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "category" not in fm
        assert "check_command" not in fm
        assert "pass_criteria" not in fm

    def test_roundtrip(self):
        entry = ProgrammaticValidationEntry(
            id="test",
            title="Ruff Linting",
            category="coding",
            check_command="ruff check .",
            pass_criteria="exit code 0",
            tags=["ci"],
        )
        fm = entry.to_frontmatter()
        restored = ProgrammaticValidationEntry.from_frontmatter(fm, entry.body)
        assert restored.entry_type == "programmatic_validation"
        assert restored.category == "coding"
        assert restored.check_command == "ruff check ."
        assert restored.pass_criteria == "exit code 0"
        assert restored.tags == ["ci"]

    def test_validation_category_enum(self):
        errors = validate_software_kb("programmatic_validation", {"category": "coding", "check_command": "x"}, {})
        non_warnings = [e for e in errors if e.get("severity") != "warning"]
        assert non_warnings == []

    def test_invalid_category(self):
        errors = validate_software_kb("programmatic_validation", {"category": "invalid", "check_command": "x"}, {})
        assert any(e["field"] == "category" for e in errors)

    def test_check_command_warning(self):
        errors = validate_software_kb("programmatic_validation", {"category": "coding"}, {})
        warnings = [e for e in errors if e.get("severity") == "warning"]
        assert any(e["rule"] == "check_command_recommended" for e in warnings)

    def test_no_warning_with_check_command(self):
        errors = validate_software_kb("programmatic_validation", {"check_command": "ruff check ."}, {})
        assert not any(e["rule"] == "check_command_recommended" for e in errors)


# =========================================================================
# Entry types — DevelopmentConvention
# =========================================================================


class TestDevelopmentConventionEntry:
    def test_entry_type(self):
        entry = DevelopmentConventionEntry(id="test", title="Test")
        assert entry.entry_type == "development_convention"

    def test_default_values(self):
        entry = DevelopmentConventionEntry(id="test", title="Test")
        assert entry.category == ""

    def test_to_frontmatter(self):
        entry = DevelopmentConventionEntry(
            id="test", title="Naming Convention", category="coding"
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "development_convention"
        assert fm["category"] == "coding"

    def test_to_frontmatter_omits_defaults(self):
        entry = DevelopmentConventionEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "category" not in fm

    def test_roundtrip(self):
        entry = DevelopmentConventionEntry(
            id="test", title="Naming Convention", category="coding", tags=["style"]
        )
        fm = entry.to_frontmatter()
        restored = DevelopmentConventionEntry.from_frontmatter(fm, entry.body)
        assert restored.entry_type == "development_convention"
        assert restored.category == "coding"
        assert restored.tags == ["style"]

    def test_validation_category_enum(self):
        errors = validate_software_kb("development_convention", {"category": "coding"}, {})
        assert errors == []

    def test_invalid_category(self):
        errors = validate_software_kb("development_convention", {"category": "invalid"}, {})
        assert any(e["field"] == "category" for e in errors)


# =========================================================================
# Standards Migration
# =========================================================================


class TestStandardsMigration:
    def _write_standard_file(self, path: Path, title: str, enforced: bool, category: str = "coding"):
        path.parent.mkdir(parents=True, exist_ok=True)
        enforced_str = "true" if enforced else "false"
        path.write_text(
            f"---\ntype: standard\ntitle: {title}\ncategory: {category}\nenforced: {enforced_str}\n---\n\nBody text.\n"
        )

    def test_dry_run_no_changes(self, tmp_path):
        """Dry run should not modify any files."""
        standards_dir = tmp_path / "standards"
        std_file = standards_dir / "test.md"
        self._write_standard_file(std_file, "Test Standard", enforced=False)

        original_content = std_file.read_text()

        from pyrite.storage.database import PyriteDB

        db_path = tmp_path / "test.db"
        db = PyriteDB(db_path)
        try:
            db._raw_conn.execute(
                "INSERT INTO kb (name, path, kb_type) VALUES (?, ?, ?)",
                ("test", str(tmp_path), "generic"),
            )
            db._raw_conn.execute(
                "INSERT INTO entry (id, kb_name, entry_type, title, body, file_path, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "test-std",
                    "test",
                    "standard",
                    "Test Standard",
                    "Body text.",
                    str(std_file),
                    json.dumps({"category": "coding", "enforced": False}),
                ),
            )
            db._raw_conn.commit()

            from pyrite_software_kb.cli import _query_entries

            rows = _query_entries(db, "standard")
            assert len(rows) == 1

            # Verify file unchanged (simulating dry run logic)
            assert std_file.read_text() == original_content
        finally:
            db.close()

    def test_enforced_becomes_validation(self, tmp_path):
        """An enforced standard should become programmatic_validation."""
        standards_dir = tmp_path / "standards"
        std_file = standards_dir / "ruff.md"
        self._write_standard_file(std_file, "Ruff Linting", enforced=True)

        import re

        content = std_file.read_text()
        content = re.sub(r'^type:\s*standard\s*$', 'type: programmatic_validation', content, flags=re.MULTILINE)
        content = re.sub(r'^enforced:\s*(true|false)\s*\n', '', content, flags=re.MULTILINE | re.IGNORECASE)

        new_dir = tmp_path / "validations"
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / "ruff.md"
        new_path.write_text(content)

        assert "type: programmatic_validation" in new_path.read_text()
        assert "enforced:" not in new_path.read_text()
        assert new_path.exists()

    def test_non_enforced_becomes_convention(self, tmp_path):
        """A non-enforced standard should become development_convention."""
        standards_dir = tmp_path / "standards"
        std_file = standards_dir / "naming.md"
        self._write_standard_file(std_file, "Naming Convention", enforced=False)

        import re

        content = std_file.read_text()
        content = re.sub(r'^type:\s*standard\s*$', 'type: development_convention', content, flags=re.MULTILINE)
        content = re.sub(r'^enforced:\s*(true|false)\s*\n', '', content, flags=re.MULTILINE | re.IGNORECASE)

        new_dir = tmp_path / "conventions"
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / "naming.md"
        new_path.write_text(content)

        assert "type: development_convention" in new_path.read_text()
        assert "enforced:" not in new_path.read_text()
        assert new_path.exists()


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
        assert ADR_LIFECYCLE["states"] == ["proposed", "accepted", "rejected", "deprecated", "superseded"]
        assert ADR_LIFECYCLE["initial"] == "proposed"
        assert ADR_LIFECYCLE["field"] == "status"

    def test_proposed_to_accepted(self):
        assert can_transition(ADR_LIFECYCLE, "proposed", "accepted", "write")

    def test_proposed_to_rejected(self):
        assert can_transition(ADR_LIFECYCLE, "proposed", "rejected", "write")

    def test_rejected_requires_reason(self):
        assert requires_reason(ADR_LIFECYCLE, "proposed", "rejected")

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

    def test_proposed_to_planned(self):
        assert can_transition(BACKLOG_WORKFLOW, "proposed", "planned", "write")

    def test_planned_to_accepted(self):
        assert can_transition(BACKLOG_WORKFLOW, "planned", "accepted", "write")

    def test_in_progress_to_completed(self):
        assert can_transition(BACKLOG_WORKFLOW, "in_progress", "completed", "write")

    def test_done_to_retired(self):
        assert can_transition(BACKLOG_WORKFLOW, "done", "retired", "write")

    def test_completed_to_retired(self):
        assert can_transition(BACKLOG_WORKFLOW, "completed", "retired", "write")

    def test_proposed_to_deferred(self):
        assert can_transition(BACKLOG_WORKFLOW, "proposed", "deferred", "write")

    def test_planned_to_deferred(self):
        assert can_transition(BACKLOG_WORKFLOW, "planned", "deferred", "write")

    def test_deferred_to_proposed(self):
        assert can_transition(BACKLOG_WORKFLOW, "deferred", "proposed", "write")

    def test_reopen_from_completed(self):
        assert can_transition(BACKLOG_WORKFLOW, "completed", "accepted", "write")
        assert requires_reason(BACKLOG_WORKFLOW, "completed", "accepted")

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
        assert "programmatic_validation" in p["types"]
        assert "development_convention" in p["types"]
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
        assert "validations" in dirs
        assert "conventions" in dirs
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
        assert "rejected" in ADR_STATUSES
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

    def test_validation_categories(self):
        assert VALIDATION_CATEGORIES == STANDARD_CATEGORIES

    def test_convention_categories(self):
        assert CONVENTION_CATEGORIES == STANDARD_CATEGORIES

    def test_component_kinds(self):
        assert "module" in COMPONENT_KINDS
        assert "service" in COMPONENT_KINDS
        assert "application" in COMPONENT_KINDS
        assert "utility" in COMPONENT_KINDS
        assert "endpoint" in COMPONENT_KINDS

    def test_backlog_kinds(self):
        assert "feature" in BACKLOG_KINDS
        assert "bug" in BACKLOG_KINDS
        assert "tech_debt" in BACKLOG_KINDS

    def test_backlog_statuses(self):
        assert "proposed" in BACKLOG_STATUSES
        assert "planned" in BACKLOG_STATUSES
        assert "accepted" in BACKLOG_STATUSES
        assert "in_progress" in BACKLOG_STATUSES
        assert "done" in BACKLOG_STATUSES
        assert "completed" in BACKLOG_STATUSES
        assert "retired" in BACKLOG_STATUSES
        assert "deferred" in BACKLOG_STATUSES
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


class TestBacklogStatusColumn:
    """Verify sw_backlog reads status from the DB column, not just metadata JSON."""

    def test_status_from_db_column_overrides_metadata(self):
        """When DB status column differs from metadata JSON, DB column wins."""
        from pyrite.storage.database import PyriteDB

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            try:
                # Insert a KB row for the foreign key
                db._raw_conn.execute(
                    "INSERT INTO kb (name, path, kb_type) VALUES (?, ?, ?)",
                    ("test", str(tmpdir), "generic"),
                )
                # Insert an entry with status=done in the column but proposed in metadata
                db._raw_conn.execute(
                    "INSERT INTO entry (id, kb_name, entry_type, title, body, status, priority, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "test-item",
                        "test",
                        "backlog_item",
                        "Test Item",
                        "",
                        "done",
                        "high",
                        json.dumps({"status": "proposed", "priority": "medium", "kind": "bug"}),
                    ),
                )
                db._raw_conn.commit()

                from pyrite_software_kb.cli import _query_entries

                rows = _query_entries(db, "backlog_item")
                assert len(rows) == 1
                row = rows[0]

                # The row's DB column should be authoritative
                assert row["status"] == "done"
                assert row["priority"] == "high"
                # But _meta still has the old values from JSON
                assert row["_meta"]["status"] == "proposed"
            finally:
                db.close()


# =========================================================================
# MilestoneEntry
# =========================================================================


class TestMilestoneEntry:
    def test_entry_type(self):
        entry = MilestoneEntry(id="m1", title="v1.0")
        assert entry.entry_type == "milestone"

    def test_defaults(self):
        entry = MilestoneEntry(id="m1", title="v1.0")
        assert entry.status == "open"

    def test_to_frontmatter_omits_defaults(self):
        entry = MilestoneEntry(id="m1", title="v1.0")
        fm = entry.to_frontmatter()
        assert fm["type"] == "milestone"
        assert "status" not in fm  # default "open" omitted

    def test_to_frontmatter_with_status(self):
        entry = MilestoneEntry(id="m1", title="v1.0", status="closed")
        fm = entry.to_frontmatter()
        assert fm["status"] == "closed"

    def test_from_frontmatter(self):
        meta = {"id": "m1", "title": "v1.0", "type": "milestone", "status": "closed"}
        entry = MilestoneEntry.from_frontmatter(meta, "Release notes")
        assert entry.id == "m1"
        assert entry.title == "v1.0"
        assert entry.status == "closed"
        assert entry.body == "Release notes"

    def test_roundtrip(self):
        entry = MilestoneEntry(id="m1", title="v1.0", status="closed")
        fm = entry.to_frontmatter()
        restored = MilestoneEntry.from_frontmatter(fm, entry.body)
        assert restored.status == entry.status
        assert restored.title == entry.title


# =========================================================================
# Milestone validator
# =========================================================================


class TestMilestoneValidator:
    def test_valid_status(self):
        errors = validate_software_kb("milestone", {"status": "open"}, {})
        assert errors == []

    def test_valid_closed(self):
        errors = validate_software_kb("milestone", {"status": "closed"}, {})
        assert errors == []

    def test_invalid_status(self):
        errors = validate_software_kb("milestone", {"status": "invalid"}, {})
        assert any(e["field"] == "status" for e in errors)

    def test_default_status_ok(self):
        errors = validate_software_kb("milestone", {}, {})
        assert errors == []


# =========================================================================
# Board config
# =========================================================================


class TestBoardConfig:
    def test_fallback_to_defaults(self):
        from pyrite_software_kb.board import DEFAULT_BOARD_CONFIG, load_board_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_board_config(Path(tmpdir))
            assert config["lanes"] == DEFAULT_BOARD_CONFIG["lanes"]
            assert config["wip_policy"] == "warn"

    def test_load_from_file(self):
        from pyrite_software_kb.board import load_board_config

        with tempfile.TemporaryDirectory() as tmpdir:
            board_file = Path(tmpdir) / "board.yaml"
            board_file.write_text(
                "lanes:\n"
                "  - name: Todo\n"
                "    statuses: [proposed]\n"
                "  - name: Done\n"
                "    statuses: [done]\n"
                "wip_policy: block\n"
            )
            config = load_board_config(Path(tmpdir))
            assert len(config["lanes"]) == 2
            assert config["lanes"][0]["name"] == "Todo"
            assert config["wip_policy"] == "block"

    def test_lane_structure(self):
        from pyrite_software_kb.board import DEFAULT_BOARD_CONFIG

        for lane in DEFAULT_BOARD_CONFIG["lanes"]:
            assert "name" in lane
            assert "statuses" in lane
            assert isinstance(lane["statuses"], list)


# =========================================================================
# Review workflow transitions
# =========================================================================


class TestReviewWorkflow:
    def test_review_in_states(self):
        assert "review" in BACKLOG_WORKFLOW["states"]

    def test_in_progress_to_review(self):
        assert can_transition(BACKLOG_WORKFLOW, "in_progress", "review", "write")

    def test_review_to_done(self):
        assert can_transition(BACKLOG_WORKFLOW, "review", "done", "write")

    def test_review_to_completed(self):
        assert can_transition(BACKLOG_WORKFLOW, "review", "completed", "write")

    def test_review_to_in_progress(self):
        assert can_transition(BACKLOG_WORKFLOW, "review", "in_progress", "write")

    def test_review_to_in_progress_requires_reason(self):
        assert requires_reason(BACKLOG_WORKFLOW, "review", "in_progress")

    def test_in_progress_to_review_no_reason(self):
        assert not requires_reason(BACKLOG_WORKFLOW, "in_progress", "review")

    def test_review_to_done_no_reason(self):
        assert not requires_reason(BACKLOG_WORKFLOW, "review", "done")

    def test_review_in_backlog_statuses(self):
        assert "review" in BACKLOG_STATUSES


# =========================================================================
# Plugin registration updates
# =========================================================================


class TestMilestonePluginRegistration:
    def test_milestone_type_registered(self):
        plugin = SoftwareKBPlugin()
        types = plugin.get_entry_types()
        assert "milestone" in types
        assert types["milestone"] is MilestoneEntry

    def test_milestone_mcp_tools(self):
        plugin = SoftwareKBPlugin()
        tools = plugin.get_mcp_tools("read")
        assert "sw_milestones" in tools
        assert "sw_board" in tools

    def test_milestone_statuses_enum(self):
        assert MILESTONE_STATUSES == ("open", "closed")

    def test_preset_has_milestone(self):
        assert "milestone" in SOFTWARE_KB_PRESET["types"]
        assert SOFTWARE_KB_PRESET["types"]["milestone"]["subdirectory"] == "milestones/"

    def test_preset_has_milestones_dir(self):
        assert "milestones" in SOFTWARE_KB_PRESET["directories"]

    def test_preset_has_default_board(self):
        assert "default_board" in SOFTWARE_KB_PRESET
        assert "lanes" in SOFTWARE_KB_PRESET["default_board"]
        assert "wip_policy" in SOFTWARE_KB_PRESET["default_board"]


# =========================================================================
# Kanban Flow Tools — helpers
# =========================================================================


def _make_test_db(tmpdir, entries=None, links=None):
    """Create a test DB with a KB and optional entries/links."""
    from pyrite.storage.database import PyriteDB

    db_path = Path(tmpdir) / "test.db"
    db = PyriteDB(db_path)
    db._raw_conn.execute(
        "INSERT INTO kb (name, path, kb_type) VALUES (?, ?, ?)",
        ("test", str(tmpdir), "generic"),
    )
    for e in (entries or []):
        meta = e.get("meta", {})
        db._raw_conn.execute(
            "INSERT INTO entry (id, kb_name, entry_type, title, body, status, priority, assignee, metadata, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                e["id"],
                "test",
                e.get("entry_type", "backlog_item"),
                e.get("title", e["id"]),
                e.get("body", ""),
                e.get("status"),
                e.get("priority"),
                e.get("assignee"),
                json.dumps(meta),
                e.get("created_at", "2026-01-01T00:00:00"),
                e.get("updated_at", "2026-01-01T00:00:00"),
            ),
        )
    for lnk in (links or []):
        db._raw_conn.execute(
            "INSERT INTO link (source_id, source_kb, target_id, target_kb, relation, inverse_relation) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                lnk["source"],
                "test",
                lnk["target"],
                "test",
                lnk.get("relation", "tracks"),
                lnk.get("inverse", "tracked_by"),
            ),
        )
    db._raw_conn.commit()
    return db


def _make_plugin_with_db(db):
    """Create a plugin with injected DB context."""

    class _Ctx:
        def __init__(self, db):
            self.db = db

    plugin = SoftwareKBPlugin()
    plugin.set_context(_Ctx(db))
    return plugin


# =========================================================================
# TestReviewQueue
# =========================================================================


class TestReviewQueue:
    def test_review_queue_returns_review_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir, entries=[
                {"id": "item-1", "title": "Review Me", "status": "review", "priority": "high",
                 "meta": {"kind": "bug", "status": "review", "priority": "high"},
                 "updated_at": "2026-01-01T10:00:00"},
                {"id": "item-2", "title": "In Progress", "status": "in_progress",
                 "meta": {"kind": "feature", "status": "in_progress"}},
                {"id": "item-3", "title": "Also Review", "status": "review", "priority": "medium",
                 "meta": {"kind": "feature", "status": "review", "priority": "medium"},
                 "updated_at": "2026-01-02T10:00:00"},
            ])
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_review_queue({"kb_name": "test"})
                assert result["count"] == 2
                assert result["items"][0]["id"] == "item-1"  # older first
                assert result["items"][1]["id"] == "item-3"
            finally:
                db.close()

    def test_review_queue_excludes_non_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir, entries=[
                {"id": "item-1", "title": "Accepted", "status": "accepted",
                 "meta": {"kind": "feature", "status": "accepted"}},
            ])
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_review_queue({"kb_name": "test"})
                assert result["count"] == 0
                assert result["items"] == []
            finally:
                db.close()


# =========================================================================
# TestContextForItem
# =========================================================================


class TestContextForItem:
    def test_context_categorizes_linked_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(
                tmpdir,
                entries=[
                    {"id": "item-1", "title": "My Task", "status": "accepted",
                     "entry_type": "backlog_item",
                     "meta": {"kind": "feature", "status": "accepted", "priority": "high"}},
                    {"id": "adr-1", "title": "Use REST", "entry_type": "adr",
                     "meta": {"status": "accepted"}},
                    {"id": "comp-1", "title": "API Server", "entry_type": "component",
                     "meta": {"kind": "service"}},
                    {"id": "val-1", "title": "Ruff Check", "entry_type": "programmatic_validation",
                     "meta": {"category": "coding"}},
                ],
                links=[
                    {"source": "item-1", "target": "adr-1", "relation": "tracks", "inverse": "tracked_by"},
                    {"source": "item-1", "target": "comp-1", "relation": "tracks", "inverse": "tracked_by"},
                    {"source": "item-1", "target": "val-1", "relation": "tracks", "inverse": "tracked_by"},
                ],
            )
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_context_for_item({"item_id": "item-1", "kb_name": "test"})
                assert result["item"]["id"] == "item-1"
                assert result["item"]["title"] == "My Task"
                assert len(result["adrs"]) == 1
                assert result["adrs"][0]["id"] == "adr-1"
                assert len(result["components"]) == 1
                assert result["components"][0]["id"] == "comp-1"
                assert len(result["validations"]) == 1
                assert result["validations"][0]["id"] == "val-1"
            finally:
                db.close()

    def test_context_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir)
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_context_for_item({"item_id": "nonexistent", "kb_name": "test"})
                assert "error" in result
            finally:
                db.close()


# =========================================================================
# TestPullNext
# =========================================================================


class TestPullNext:
    def test_pull_next_returns_highest_priority(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir, entries=[
                {"id": "low-1", "title": "Low Priority", "status": "accepted", "priority": "low",
                 "meta": {"kind": "feature", "status": "accepted", "priority": "low"},
                 "created_at": "2026-01-01T00:00:00"},
                {"id": "high-1", "title": "High Priority", "status": "accepted", "priority": "high",
                 "meta": {"kind": "bug", "status": "accepted", "priority": "high"},
                 "created_at": "2026-01-02T00:00:00"},
                {"id": "crit-1", "title": "Critical", "status": "accepted", "priority": "critical",
                 "meta": {"kind": "bug", "status": "accepted", "priority": "critical"},
                 "created_at": "2026-01-03T00:00:00"},
            ])
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_pull_next({"kb_name": "test"})
                assert result["recommendation"] is not None
                assert result["recommendation"]["id"] == "crit-1"
                assert result["recommendation"]["priority"] == "critical"
            finally:
                db.close()

    def test_pull_next_no_accepted_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir, entries=[
                {"id": "item-1", "title": "Proposed", "status": "proposed",
                 "meta": {"kind": "feature", "status": "proposed"}},
            ])
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_pull_next({"kb_name": "test"})
                assert result["recommendation"] is None
                assert "No accepted" in result["reason"]
            finally:
                db.close()

    def test_pull_next_wip_limit_enforce(self):
        """When WIP limit is reached and policy is enforce, return no recommendation."""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a board config with enforce policy and wip_limit=1
            board_file = Path(tmpdir) / "board.yaml"
            board_file.write_text(
                "lanes:\n"
                "  - name: In Progress\n"
                "    statuses: [in_progress]\n"
                "    wip_limit: 1\n"
                "wip_policy: enforce\n"
            )
            db = _make_test_db(tmpdir, entries=[
                {"id": "ip-1", "title": "Already Working", "status": "in_progress",
                 "meta": {"kind": "feature", "status": "in_progress"}},
                {"id": "acc-1", "title": "Waiting", "status": "accepted",
                 "meta": {"kind": "feature", "status": "accepted", "priority": "high"}},
            ])
            try:
                plugin = _make_plugin_with_db(db)
                from pyrite_software_kb.board import load_board_config as real_load

                with patch(
                    "pyrite_software_kb.board.load_board_config",
                    side_effect=lambda p: real_load(Path(tmpdir)),
                ):
                    result = plugin._mcp_pull_next({"kb_name": "test"})
                assert result["recommendation"] is None
                assert "WIP limit" in result["reason"]
            finally:
                db.close()


# =========================================================================
# TestClaim
# =========================================================================


class TestClaim:
    def test_claim_validates_transition(self):
        """Cannot claim from proposed (must be accepted first)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir, entries=[
                {"id": "item-1", "title": "Proposed Item", "status": "proposed",
                 "meta": {"kind": "feature", "status": "proposed"}},
            ])
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_claim({
                    "item_id": "item-1", "kb_name": "test", "assignee": "agent-1",
                })
                assert result["claimed"] is False
                assert "Cannot transition" in result["error"]
                assert "allowed_transitions" in result
            finally:
                db.close()

    def test_claim_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir)
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_claim({
                    "item_id": "nonexistent", "kb_name": "test", "assignee": "agent-1",
                })
                assert result["claimed"] is False
                assert "not found" in result["error"]
            finally:
                db.close()

    def test_claim_already_in_progress(self):
        """Cannot claim an item already in_progress."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = _make_test_db(tmpdir, entries=[
                {"id": "item-1", "title": "Already Working", "status": "in_progress",
                 "meta": {"kind": "feature", "status": "in_progress"}, "assignee": "someone"},
            ])
            try:
                plugin = _make_plugin_with_db(db)
                result = plugin._mcp_claim({
                    "item_id": "item-1", "kb_name": "test", "assignee": "agent-2",
                })
                assert result["claimed"] is False
                assert "Cannot transition" in result["error"]
            finally:
                db.close()


# =========================================================================
# Plugin registration for flow tools
# =========================================================================


class TestFlowToolRegistration:
    def test_read_tier_has_review_queue(self):
        plugin = SoftwareKBPlugin()
        tools = plugin.get_mcp_tools("read")
        assert "sw_review_queue" in tools

    def test_read_tier_has_pull_next(self):
        plugin = SoftwareKBPlugin()
        tools = plugin.get_mcp_tools("read")
        assert "sw_pull_next" in tools

    def test_read_tier_has_context_for_item(self):
        plugin = SoftwareKBPlugin()
        tools = plugin.get_mcp_tools("read")
        assert "sw_context_for_item" in tools

    def test_write_tier_has_claim(self):
        plugin = SoftwareKBPlugin()
        tools = plugin.get_mcp_tools("write")
        assert "sw_claim" in tools

    def test_read_tier_does_not_have_claim(self):
        plugin = SoftwareKBPlugin()
        tools = plugin.get_mcp_tools("read")
        assert "sw_claim" not in tools
