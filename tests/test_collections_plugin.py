"""Tests for Collections Phase 5 — plugin-defined collection types."""


class TestPluginProtocolCollectionTypes:
    """Test get_collection_types on the plugin protocol."""

    def test_protocol_has_get_collection_types(self):
        """Protocol defines get_collection_types method."""
        from pyrite.plugins.protocol import PyritePlugin
        assert hasattr(PyritePlugin, "get_collection_types")

    def test_protocol_method_callable(self):
        """A minimal plugin can implement get_collection_types."""
        class TestPlugin:
            name = "test"

            def get_collection_types(self):
                return {
                    "evidence-board": {
                        "description": "Evidence board for investigations",
                        "default_view": "kanban",
                        "fields": {"confidence": {"type": "select", "options": ["low", "medium", "high"]}},
                        "ai_instructions": "Use for organizing evidence",
                        "icon": "shield",
                    }
                }

        plugin = TestPlugin()
        types = plugin.get_collection_types()
        assert "evidence-board" in types
        assert types["evidence-board"]["default_view"] == "kanban"
        assert types["evidence-board"]["icon"] == "shield"


class TestRegistryCollectionTypes:
    """Test registry aggregation of collection types."""

    def test_get_all_collection_types_empty(self):
        """Registry returns empty dict when no plugins provide types."""
        from pyrite.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        reg._discovered = True  # Skip discovery
        result = reg.get_all_collection_types()
        assert result == {}

    def test_get_all_collection_types_merges(self):
        """Registry merges collection types from multiple plugins."""
        from pyrite.plugins.registry import PluginRegistry

        class PluginA:
            name = "plugin-a"
            def get_collection_types(self):
                return {"board": {"description": "A board", "default_view": "kanban"}}

        class PluginB:
            name = "plugin-b"
            def get_collection_types(self):
                return {"gallery": {"description": "A gallery", "default_view": "gallery"}}

        reg = PluginRegistry()
        reg._discovered = True
        reg._plugins = {"plugin-a": PluginA(), "plugin-b": PluginB()}

        result = reg.get_all_collection_types()
        assert "board" in result
        assert "gallery" in result
        assert result["board"]["default_view"] == "kanban"
        assert result["gallery"]["default_view"] == "gallery"

    def test_get_all_collection_types_handles_errors(self):
        """Registry handles plugin errors gracefully."""
        from pyrite.plugins.registry import PluginRegistry

        class BadPlugin:
            name = "bad"
            def get_collection_types(self):
                raise RuntimeError("oops")

        reg = PluginRegistry()
        reg._discovered = True
        reg._plugins = {"bad": BadPlugin()}

        result = reg.get_all_collection_types()
        assert result == {}

    def test_get_all_collection_types_skips_plugins_without_method(self):
        """Registry skips plugins that don't implement get_collection_types."""
        from pyrite.plugins.registry import PluginRegistry

        class SimplePlugin:
            name = "simple"

        reg = PluginRegistry()
        reg._discovered = True
        reg._plugins = {"simple": SimplePlugin()}

        result = reg.get_all_collection_types()
        assert result == {}


class TestCollectionTypesEndpoint:
    """Test the collection types API endpoint."""

    def test_collection_types_endpoint_exists(self):
        """GET /api/collections/types endpoint is defined."""
        from pyrite.server.api import create_app

        app = create_app()
        routes = [r.path for r in app.routes]
        assert "/api/collections/types" in routes


class TestCollectionEntryType:
    """Test CollectionEntry with collection_type field."""

    def test_collection_entry_has_collection_type_field(self):
        """CollectionEntry has collection_type with default 'generic'."""
        from pyrite.models.collection import CollectionEntry

        entry = CollectionEntry(id="test", title="Test")
        assert entry.collection_type == "generic"

    def test_collection_entry_custom_type(self):
        """CollectionEntry accepts custom collection_type."""
        from pyrite.models.collection import CollectionEntry

        entry = CollectionEntry(id="test", title="Test", collection_type="evidence-board")
        assert entry.collection_type == "evidence-board"

    def test_collection_entry_type_in_frontmatter(self):
        """collection_type appears in frontmatter when not default."""
        from pyrite.models.collection import CollectionEntry

        entry = CollectionEntry(id="test", title="Test", collection_type="board")
        fm = entry.to_frontmatter()
        assert fm.get("collection_type") == "board"

    def test_collection_entry_type_omitted_when_default(self):
        """collection_type is omitted from frontmatter when 'generic'."""
        from pyrite.models.collection import CollectionEntry

        entry = CollectionEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "collection_type" not in fm

    def test_collection_entry_from_frontmatter_with_type(self):
        """CollectionEntry.from_frontmatter reads collection_type."""
        from pyrite.models.collection import CollectionEntry

        meta = {"id": "test", "title": "Test", "collection_type": "evidence-board"}
        entry = CollectionEntry.from_frontmatter(meta, "body")
        assert entry.collection_type == "evidence-board"
