"""Tests for build_entry() factory — branch coverage for all entry types."""

import logging

import pytest

from pyrite.models.collection import CollectionEntry
from pyrite.models.core_types import (
    EventEntry,
    NoteEntry,
    OrganizationEntry,
    PersonEntry,
    entry_from_frontmatter,
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


class TestEntryFromFrontmatterMissingType:
    """Warn when frontmatter lacks `type:` and factory falls back to note."""

    def test_missing_type_logs_warning(self, caplog):
        """entry_from_frontmatter should log a warning when type is absent."""
        meta = {"id": "x", "title": "y"}

        with caplog.at_level(logging.WARNING, logger="pyrite.models.core_types"):
            entry = entry_from_frontmatter(meta, "some body")

        # Behavior preserved: still builds a NoteEntry fallback.
        assert isinstance(entry, NoteEntry)

        # Warning surfaced so the silent fallback is visible.
        warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING
            and r.name == "pyrite.models.core_types"
        ]
        assert warnings, "expected a warning about missing type fallback"
        msg = warnings[0].getMessage().lower()
        assert "type" in msg
        assert "note" in msg  # fallback type
        assert "x" in warnings[0].getMessage()  # entry id

    def test_explicit_type_does_not_warn(self, caplog):
        """When frontmatter has an explicit type, no fallback warning is emitted."""
        meta = {"id": "x", "title": "y", "type": "note"}

        with caplog.at_level(logging.WARNING, logger="pyrite.models.core_types"):
            entry_from_frontmatter(meta, "body")

        fallback_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING
            and r.name == "pyrite.models.core_types"
            and "fallback" in r.getMessage().lower()
        ]
        assert not fallback_warnings
