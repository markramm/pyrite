"""Tests for build_entry() factory — branch coverage for all entry types."""

import pytest

from pyrite.models.collection import CollectionEntry
from pyrite.models.core_types import (
    EventEntry,
    NoteEntry,
    OrganizationEntry,
    PersonEntry,
)
from pyrite.models.factory import build_entry
from pyrite.models.generic import GenericEntry


class TestBuildEntryFactory:
    """Test each branch in build_entry()."""

    def test_build_event(self):
        entry = build_entry(
            "event",
            entry_id="2026-01-01--test",
            title="Test Event",
            body="Body",
            date="2026-01-01",
            importance=8,
            location="NYC",
            status="confirmed",
            participants=["Alice", "Bob"],
        )
        assert isinstance(entry, EventEntry)
        assert entry.id == "2026-01-01--test"
        assert entry.date == "2026-01-01"
        assert entry.importance == 8
        assert entry.location == "NYC"
        assert entry.status == "confirmed"
        assert entry.participants == ["Alice", "Bob"]

    def test_build_person(self):
        entry = build_entry(
            "person",
            entry_id="jane-doe",
            title="Jane Doe",
            body="Bio",
            role="Engineer",
            importance=7,
        )
        assert isinstance(entry, PersonEntry)
        assert entry.role == "Engineer"
        assert entry.importance == 7

    def test_build_organization(self):
        entry = build_entry(
            "organization",
            entry_id="acme-corp",
            title="Acme Corp",
            importance=6,
        )
        assert isinstance(entry, OrganizationEntry)
        assert entry.importance == 6

    def test_build_collection(self):
        entry = build_entry(
            "collection",
            entry_id="collection-notes",
            title="Notes",
            source_type="folder",
            view_config={"default_view": "table"},
            folder_path="notes",
        )
        assert isinstance(entry, CollectionEntry)
        assert entry.source_type == "folder"
        assert entry.view_config == {"default_view": "table"}
        assert entry.folder_path == "notes"

    def test_build_note_via_registry(self):
        """'note' is in ENTRY_TYPE_REGISTRY, so it takes the registry branch."""
        entry = build_entry(
            "note",
            entry_id="my-note",
            title="My Note",
            body="Content",
            tags=["test"],
        )
        assert isinstance(entry, NoteEntry)
        assert entry.title == "My Note"
        assert entry.tags == ["test"]

    def test_build_unknown_type_generic(self):
        """Unknown types not in registry should fall back to GenericEntry."""
        entry = build_entry(
            "alien_artifact",
            entry_id="ufo-1",
            title="UFO Sighting",
            body="Details",
            tags=["x-files"],
            metadata={"origin": "mars"},
        )
        assert isinstance(entry, GenericEntry)
        assert entry.entry_type == "alien_artifact"
        assert entry.metadata == {"origin": "mars"}

    def test_build_entry_auto_id(self):
        """When entry_id is None, ID should be generated from title."""
        entry = build_entry("note", title="My Cool Note")
        assert entry.id == "my-cool-note"
