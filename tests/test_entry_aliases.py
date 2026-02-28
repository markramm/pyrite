"""Tests for entry aliases feature."""
import json
import pytest


class TestEntryAliasesModel:
    """Test that Entry has aliases field."""

    def test_entry_has_aliases_field(self):
        """Entry subclass has aliases field with default empty list."""
        from pyrite.models.core_types import NoteEntry
        entry = NoteEntry(id="test", title="Test", aliases=["Alias1", "Alias2"])
        assert entry.aliases == ["Alias1", "Alias2"]

    def test_aliases_default_empty(self):
        """Aliases defaults to empty list."""
        from pyrite.models.core_types import NoteEntry
        entry = NoteEntry(id="test", title="Test")
        assert entry.aliases == []

    def test_aliases_in_frontmatter(self):
        """Aliases round-trip through frontmatter."""
        from pyrite.models.core_types import NoteEntry
        entry = NoteEntry(id="test", title="Test", aliases=["CIA", "The Agency"])
        fm = entry.to_frontmatter()
        assert fm["aliases"] == ["CIA", "The Agency"]

        # Round-trip
        entry2 = NoteEntry.from_frontmatter(fm, "body text")
        assert entry2.aliases == ["CIA", "The Agency"]

    def test_aliases_omitted_when_empty(self):
        """Empty aliases not included in frontmatter."""
        from pyrite.models.core_types import NoteEntry
        entry = NoteEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "aliases" not in fm

    def test_entry_title_schema_has_aliases(self):
        """EntryTitle schema includes aliases field."""
        from pyrite.server.schemas import EntryTitle
        et = EntryTitle(id="x", title="X", kb_name="kb", entry_type="note", aliases=["A", "B"])
        assert et.aliases == ["A", "B"]

    def test_entry_title_schema_aliases_default(self):
        """EntryTitle aliases defaults to empty list."""
        from pyrite.server.schemas import EntryTitle
        et = EntryTitle(id="x", title="X", kb_name="kb", entry_type="note")
        assert et.aliases == []


class TestAliasesFromFrontmatter:
    """Test all core types parse aliases."""

    @pytest.mark.parametrize("entry_class_name", [
        "NoteEntry", "PersonEntry", "OrganizationEntry", "EventEntry",
        "DocumentEntry", "TopicEntry", "RelationshipEntry", "TimelineEntry",
    ])
    def test_core_type_parses_aliases(self, entry_class_name):
        """Each core entry type parses aliases from frontmatter."""
        import pyrite.models.core_types as ct
        cls = getattr(ct, entry_class_name)
        meta = {"id": "test", "title": "Test", "aliases": ["Alias1"]}
        if entry_class_name == "EventEntry":
            meta["date"] = "2024-01-01"
        entry = cls.from_frontmatter(meta, "body")
        assert entry.aliases == ["Alias1"]

    def test_generic_entry_parses_aliases(self):
        """GenericEntry parses aliases from frontmatter."""
        from pyrite.models.generic import GenericEntry
        meta = {"id": "test", "title": "Test", "type": "custom", "aliases": ["Alt"]}
        entry = GenericEntry.from_frontmatter(meta, "body")
        assert entry.aliases == ["Alt"]

    def test_collection_entry_parses_aliases(self):
        """CollectionEntry parses aliases from frontmatter."""
        from pyrite.models.collection import CollectionEntry
        meta = {"id": "test", "title": "Test", "aliases": ["Alt"]}
        entry = CollectionEntry.from_frontmatter(meta, "body")
        assert entry.aliases == ["Alt"]

    def test_collection_from_yaml_parses_aliases(self):
        """CollectionEntry.from_collection_yaml parses aliases."""
        from pyrite.models.collection import CollectionEntry
        yaml_data = {"title": "Test", "aliases": ["Alt"]}
        entry = CollectionEntry.from_collection_yaml(yaml_data, "some/path")
        assert entry.aliases == ["Alt"]
