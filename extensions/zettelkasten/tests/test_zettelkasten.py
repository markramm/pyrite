"""Tests for the Zettelkasten extension."""

from pyrite_zettelkasten.entry_types import LiteratureNoteEntry, ZettelEntry
from pyrite_zettelkasten.plugin import ZettelkastenPlugin
from pyrite_zettelkasten.preset import ZETTELKASTEN_PRESET
from pyrite_zettelkasten.validators import validate_zettel

from pyrite.plugins.registry import PluginRegistry

# =========================================================================
# Plugin registration
# =========================================================================


class TestPluginRegistration:
    def test_plugin_has_name(self):
        plugin = ZettelkastenPlugin()
        assert plugin.name == "zettelkasten"

    def test_register_with_registry(self):
        registry = PluginRegistry()
        plugin = ZettelkastenPlugin()
        registry.register(plugin)
        assert "zettelkasten" in registry.list_plugins()

    def test_entry_types_registered(self):
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        types = registry.get_all_entry_types()
        assert "zettel" in types
        assert "literature_note" in types
        assert types["zettel"] is ZettelEntry
        assert types["literature_note"] is LiteratureNoteEntry

    def test_relationship_types_registered(self):
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        rels = registry.get_all_relationship_types()
        assert "elaborates" in rels
        assert "branches_from" in rels
        assert "synthesizes" in rels
        assert rels["elaborates"]["inverse"] == "elaborated_by"
        assert rels["branches_from"]["inverse"] == "has_branch"

    def test_validators_registered(self):
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        validators = registry.get_all_validators()
        assert validate_zettel in validators

    def test_cli_commands_registered(self):
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        commands = registry.get_all_cli_commands()
        cmd_names = [name for name, _ in commands]
        assert "zettel" in cmd_names

    def test_mcp_tools_registered(self):
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        tools = registry.get_all_mcp_tools("read")
        assert "zettel_inbox" in tools
        assert "zettel_graph" in tools

    def test_kb_presets_registered(self):
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        presets = registry.get_all_kb_presets()
        assert "zettelkasten" in presets

    def test_kb_types_registered(self):
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        kb_types = registry.get_all_kb_types()
        assert "zettelkasten" in kb_types


# =========================================================================
# Entry types
# =========================================================================


class TestZettelEntry:
    def test_default_values(self):
        entry = ZettelEntry(id="test", title="Test")
        assert entry.entry_type == "zettel"
        assert entry.zettel_type == "fleeting"
        assert entry.maturity == "seed"
        assert entry.source_ref == ""
        assert entry.processing_stage == ""

    def test_to_frontmatter(self):
        entry = ZettelEntry(
            id="test",
            title="Test",
            zettel_type="permanent",
            maturity="evergreen",
            source_ref="ref-123",
            processing_stage="connect",
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "zettel"
        assert fm["zettel_type"] == "permanent"
        assert fm["maturity"] == "evergreen"
        assert fm["source_ref"] == "ref-123"
        assert fm["processing_stage"] == "connect"

    def test_to_frontmatter_omits_defaults(self):
        entry = ZettelEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "zettel_type" not in fm  # fleeting is default
        assert "maturity" not in fm  # seed is default
        assert "source_ref" not in fm
        assert "processing_stage" not in fm

    def test_from_frontmatter(self):
        meta = {
            "id": "test",
            "title": "Test Note",
            "type": "zettel",
            "zettel_type": "permanent",
            "maturity": "sapling",
            "source_ref": "src-1",
            "processing_stage": "review",
            "tags": ["test"],
        }
        entry = ZettelEntry.from_frontmatter(meta, "Body text")
        assert entry.id == "test"
        assert entry.title == "Test Note"
        assert entry.zettel_type == "permanent"
        assert entry.maturity == "sapling"
        assert entry.source_ref == "src-1"
        assert entry.processing_stage == "review"
        assert entry.body == "Body text"
        assert entry.tags == ["test"]

    def test_from_frontmatter_generates_id(self):
        meta = {"title": "My Great Note", "type": "zettel"}
        entry = ZettelEntry.from_frontmatter(meta, "")
        assert entry.id == "my-great-note"

    def test_roundtrip_markdown(self):
        entry = ZettelEntry(
            id="test-note",
            title="Test Note",
            body="Some content",
            zettel_type="permanent",
            maturity="sapling",
            tags=["knowledge", "test"],
        )
        md = entry.to_markdown()
        assert "zettel_type: permanent" in md
        assert "maturity: sapling" in md
        assert "Some content" in md


class TestLiteratureNoteEntry:
    def test_default_values(self):
        entry = LiteratureNoteEntry(id="test", title="Test")
        assert entry.entry_type == "literature_note"
        assert entry.source_work == ""
        assert entry.author == ""
        assert entry.page_refs == []

    def test_to_frontmatter(self):
        entry = LiteratureNoteEntry(
            id="test",
            title="Notes on Book X",
            source_work="Book X",
            author="Author Y",
            page_refs=["p.42", "p.99"],
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "literature_note"
        assert fm["source_work"] == "Book X"
        assert fm["author"] == "Author Y"
        assert fm["page_refs"] == ["p.42", "p.99"]

    def test_from_frontmatter(self):
        meta = {
            "id": "test",
            "title": "Notes on Book X",
            "type": "literature_note",
            "source_work": "Book X",
            "author": "Author Y",
            "page_refs": ["p.42"],
        }
        entry = LiteratureNoteEntry.from_frontmatter(meta, "Notes here")
        assert entry.source_work == "Book X"
        assert entry.author == "Author Y"
        assert entry.page_refs == ["p.42"]
        assert entry.body == "Notes here"


# =========================================================================
# Validators
# =========================================================================


class TestValidators:
    def test_fleeting_requires_processing_stage(self):
        errors = validate_zettel("zettel", {"zettel_type": "fleeting"}, {})
        assert any(e["rule"] == "required_for_fleeting" for e in errors)

    def test_fleeting_with_stage_ok(self):
        errors = validate_zettel(
            "zettel", {"zettel_type": "fleeting", "processing_stage": "capture"}, {}
        )
        assert not any(e["rule"] == "required_for_fleeting" for e in errors)

    def test_literature_note_requires_source_work(self):
        errors = validate_zettel("literature_note", {}, {})
        assert any(e["field"] == "source_work" for e in errors)

    def test_literature_note_with_source_ok(self):
        errors = validate_zettel("literature_note", {"source_work": "Book X"}, {})
        assert not any(e["field"] == "source_work" for e in errors)

    def test_permanent_warns_no_links(self):
        errors = validate_zettel("zettel", {"zettel_type": "permanent"}, {})
        warnings = [e for e in errors if e.get("severity") == "warning"]
        assert any(e["rule"] == "permanent_should_link" for e in warnings)

    def test_permanent_with_links_no_warning(self):
        errors = validate_zettel(
            "zettel",
            {"zettel_type": "permanent", "links": [{"target": "x", "relation": "related"}]},
            {},
        )
        warnings = [e for e in errors if e.get("severity") == "warning"]
        assert not any(e["rule"] == "permanent_should_link" for e in warnings)

    def test_hub_requires_3_links(self):
        errors = validate_zettel(
            "zettel",
            {"zettel_type": "hub", "links": [{"target": "a"}, {"target": "b"}]},
            {},
        )
        non_warnings = [e for e in errors if e.get("severity") != "warning"]
        assert any(e["rule"] == "hub_min_links" for e in non_warnings)

    def test_hub_with_3_links_ok(self):
        errors = validate_zettel(
            "zettel",
            {
                "zettel_type": "hub",
                "links": [{"target": "a"}, {"target": "b"}, {"target": "c"}],
            },
            {},
        )
        assert not any(e["rule"] == "hub_min_links" for e in errors)

    def test_invalid_zettel_type(self):
        errors = validate_zettel("zettel", {"zettel_type": "invalid"}, {})
        assert any(e["field"] == "zettel_type" for e in errors)

    def test_invalid_maturity(self):
        errors = validate_zettel(
            "zettel",
            {"zettel_type": "permanent", "maturity": "invalid", "links": [{"target": "x"}]},
            {},
        )
        assert any(e["field"] == "maturity" for e in errors)

    def test_invalid_processing_stage(self):
        errors = validate_zettel(
            "zettel",
            {"zettel_type": "fleeting", "processing_stage": "invalid"},
            {},
        )
        assert any(e["field"] == "processing_stage" for e in errors)

    def test_ignores_unrelated_types(self):
        errors = validate_zettel("note", {"title": "regular note"}, {})
        assert errors == []

    def test_ignores_event_type(self):
        errors = validate_zettel("event", {"title": "something"}, {})
        assert errors == []


# =========================================================================
# Preset
# =========================================================================


class TestPreset:
    def test_preset_structure(self):
        p = ZETTELKASTEN_PRESET
        assert p["name"] == "my-zettelkasten"
        assert "zettel" in p["types"]
        assert "literature_note" in p["types"]
        assert p["policies"]["private"] is True
        assert p["policies"]["single_author"] is True
        assert p["validation"]["enforce"] is True

    def test_preset_zettel_type(self):
        zt = ZETTELKASTEN_PRESET["types"]["zettel"]
        assert "title" in zt["required"]
        assert "zettel_type" in zt["optional"]
        assert "maturity" in zt["optional"]

    def test_preset_literature_type(self):
        lt = ZETTELKASTEN_PRESET["types"]["literature_note"]
        assert "source_work" in lt["required"]

    def test_preset_directories(self):
        assert "zettels" in ZETTELKASTEN_PRESET["directories"]
        assert "literature" in ZETTELKASTEN_PRESET["directories"]


# =========================================================================
# Entry type resolution via core
# =========================================================================


class TestCoreIntegration:
    """Test that the plugin integrates correctly with pyrite core when registered."""

    def test_entry_class_resolution(self):
        """Plugin entry types resolve via get_entry_class when registered."""
        from pyrite.plugins.registry import PluginRegistry

        # Use a fresh registry
        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())

        # Temporarily replace global registry
        import pyrite.plugins.registry as reg_module

        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import get_entry_class

            cls = get_entry_class("zettel")
            assert cls is ZettelEntry

            cls = get_entry_class("literature_note")
            assert cls is LiteratureNoteEntry

            # Core types still work
            from pyrite.models.core_types import NoteEntry

            cls = get_entry_class("note")
            assert cls is NoteEntry
        finally:
            reg_module._registry = old

    def test_entry_from_frontmatter_resolution(self):
        """Plugin entry types resolve via entry_from_frontmatter when registered."""
        import pyrite.plugins.registry as reg_module
        from pyrite.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())

        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import entry_from_frontmatter

            entry = entry_from_frontmatter(
                {"type": "zettel", "title": "Test", "zettel_type": "permanent"},
                "Body",
            )
            assert isinstance(entry, ZettelEntry)
            assert entry.zettel_type == "permanent"

            entry = entry_from_frontmatter(
                {"type": "literature_note", "title": "Test", "source_work": "Book"},
                "Notes",
            )
            assert isinstance(entry, LiteratureNoteEntry)
            assert entry.source_work == "Book"
        finally:
            reg_module._registry = old

    def test_relationship_types_merged(self):
        """Plugin relationship types merge into schema."""
        import pyrite.plugins.registry as reg_module
        from pyrite.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())

        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.schema import get_all_relationship_types, get_inverse_relation

            all_rels = get_all_relationship_types()
            assert "elaborates" in all_rels
            assert "branches_from" in all_rels

            assert get_inverse_relation("elaborates") == "elaborated_by"
            assert get_inverse_relation("branches_from") == "has_branch"
            # Core types still work
            assert get_inverse_relation("owns") == "owned_by"
        finally:
            reg_module._registry = old
