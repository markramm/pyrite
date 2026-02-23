"""
Tests for entry models.
"""

import re
import tempfile
from pathlib import Path

import pytest

from pyrite.models import EventEntry
from pyrite.models.core_types import OrganizationEntry, PersonEntry
from pyrite.schema import EventStatus, ResearchStatus


class TestEventEntry:
    """Tests for EventEntry model."""

    def test_create_event(self):
        """Test creating an event entry."""
        event = EventEntry.create(
            date="2025-01-20",
            title="Executive Orders Blitz",
            body="The administration signed 47 executive orders on day one.",
            importance=9,
            participants=["Stephen Miller", "Donald Trump"],
            tags=["executive-orders", "day-one"],
        )
        assert event.date == "2025-01-20"
        assert event.id == "2025-01-20--executive-orders-blitz"
        assert event.importance == 9

    def test_event_to_markdown(self):
        """Test converting event to markdown."""
        event = EventEntry(
            id="2025-01-06--minneapolis-raids",
            title="ICE Raids Minneapolis",
            date="2025-01-06",
            importance=8,
            body="Federal agents conducted sweeping raids.",
        )
        md = event.to_markdown()
        assert "---" in md
        assert "date: '2025-01-06'" in md or "date: 2025-01-06" in md
        assert "importance: 8" in md
        assert "Federal agents" in md

    def test_event_from_markdown(self):
        """Test parsing event from markdown."""
        md = """---
id: 2025-01-20--test-event
date: '2025-01-20'
importance: 7
title: Test Event
status: confirmed
participants:
  - Person One
  - Person Two
tags:
  - test
  - example
---

This is the event body.
"""
        event = EventEntry.from_markdown(md)
        assert event.id == "2025-01-20--test-event"
        assert event.date == "2025-01-20"
        assert event.importance == 7
        assert event.status == EventStatus.CONFIRMED
        assert len(event.participants) == 2
        assert "This is the event body" in event.body

    def test_event_validation(self):
        """Test event validation."""
        # Valid event
        event = EventEntry(
            id="2025-01-20--valid", title="Valid Event", date="2025-01-20", importance=5
        )
        errors = event.validate()
        assert len(errors) == 0

        # Missing date
        bad_event = EventEntry(id="missing-date", title="Bad Event", date="", importance=5)
        errors = bad_event.validate()
        assert any("date" in e.lower() for e in errors)

        # Invalid importance
        bad_event2 = EventEntry(
            id="2025-01-20--bad", title="Bad Event", date="2025-01-20", importance=15
        )
        errors = bad_event2.validate()
        assert any("importance" in e.lower() for e in errors)


class TestPersonEntry:
    """Tests for PersonEntry model."""

    def test_create_person(self):
        """Test creating a person entry."""
        name = "Stephen Miller"
        entry_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        actor = PersonEntry(
            id=entry_id,
            title=name,
            role="architect",
            importance=10,
            tags=["immigration", "schedule-f"],
        )
        assert actor.entry_type == "person"
        assert actor.title == "Stephen Miller"
        assert actor.role == "architect"
        assert actor.importance == 10

    def test_person_create_classmethod(self):
        """Test PersonEntry.create() class method."""
        actor = PersonEntry.create(
            name="Stephen Miller",
            role="architect",
            importance=10,
        )
        assert actor.entry_type == "person"
        assert actor.title == "Stephen Miller"
        assert actor.role == "architect"

    def test_person_to_markdown(self):
        """Test converting person entry to markdown."""
        entry = PersonEntry(
            id="miller-stephen",
            title="Stephen Miller",
            role="architect",
            importance=10,
            body="## Quick Facts\n- Primary immigration architect",
        )
        md = entry.to_markdown()
        assert "---" in md
        assert "type: person" in md
        assert "role: architect" in md
        assert "Quick Facts" in md

    def test_person_from_markdown(self):
        """Test parsing person entry from markdown."""
        md = """---
id: miller-stephen
title: Stephen Miller
type: person
role: architect
importance: 10
tags:
  - immigration
---

Key immigration policy architect.
"""
        entry = PersonEntry.from_markdown(md)
        assert entry.title == "Stephen Miller"
        assert entry.entry_type == "person"
        assert entry.role == "architect"
        assert entry.importance == 10
        assert "immigration policy architect" in entry.body

    def test_person_with_sources(self):
        """Test person entry with sources."""
        entry = PersonEntry(id="test-person", title="Test Person")
        entry.add_source(
            title="New York Times Article",
            url="https://nytimes.com/article",
            outlet="New York Times",
            verified=True,
        )
        assert len(entry.sources) == 1
        assert entry.sources[0].verified is True


class TestOrganizationEntry:
    """Tests for OrganizationEntry model."""

    def test_create_organization(self):
        """Test creating an organization entry."""
        org = OrganizationEntry.create(
            name="Heritage Foundation",
            founded="1973",
            jurisdiction="US",
        )
        assert org.entry_type == "organization"
        assert org.id == "heritage-foundation"
        assert org.founded == "1973"

    def test_organization_from_markdown(self):
        """Test parsing organization entry from markdown."""
        md = """---
title: "Heritage Foundation"
type: organization
importance: 9
founded: '1973'
jurisdiction: US
tags:
  - think-tank
  - project-2025
research_status: complete
---

## Overview

The Heritage Foundation is a conservative think tank...
"""
        entry = OrganizationEntry.from_markdown(md)
        assert entry.title == "Heritage Foundation"
        assert entry.entry_type == "organization"
        assert entry.importance == 9
        assert entry.founded == "1973"
        assert entry.research_status == ResearchStatus.COMPLETE
        assert "conservative think tank" in entry.body


class TestEntryRoundtrip:
    """Test roundtrip serialization."""

    def test_event_roundtrip(self):
        """Test event save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test-event.md"

            original = EventEntry.create(
                date="2025-01-20",
                title="Test Event",
                body="Test body content.",
                importance=8,
                participants=["Actor One"],
                tags=["test"],
            )
            original.add_source(title="Source", url="https://example.com")

            original.save(path)
            loaded = EventEntry.load(path)

            assert loaded.id == original.id
            assert loaded.date == original.date
            assert loaded.importance == original.importance
            assert len(loaded.sources) == 1

    def test_person_roundtrip(self):
        """Test person entry save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test-person.md"

            original = PersonEntry.create(name="John Smith", role="operative", importance=6)
            original.body = "## Background\n\nJohn Smith is..."
            original.tags = ["test", "actor"]
            original.research_status = ResearchStatus.DRAFT

            original.save(path)
            loaded = PersonEntry.load(path)

            assert loaded.id == original.id
            assert loaded.role == "operative"
            assert loaded.research_status == ResearchStatus.DRAFT
            assert "John Smith is" in loaded.body


class TestLoadExistingKBs:
    """Tests that load actual entries from existing KBs.

    These tests verify compatibility with existing data formats.
    """

    @pytest.fixture
    def cascade_series_path(self):
        """Path to CascadeSeries if available."""
        path = Path.home() / "CascadeSeries"
        if path.exists():
            return path
        pytest.skip("CascadeSeries not found")

    def test_load_timeline_event(self, cascade_series_path):
        """Test loading an actual timeline event."""
        events_dir = cascade_series_path / "timeline" / "hugo-site" / "content" / "events"
        if not events_dir.exists():
            pytest.skip("Timeline events not found")

        # Find an event file
        event_files = list(events_dir.glob("*.md"))
        if not event_files:
            pytest.skip("No event files found")

        event_file = event_files[0]
        event = EventEntry.load(event_file)

        assert event.id is not None
        assert event.title is not None
        assert event.date is not None

    def test_load_research_actor(self, cascade_series_path):
        """Test loading an actual research actor."""
        actors_dir = cascade_series_path / "research-kb" / "actors"
        if not actors_dir.exists():
            pytest.skip("Research actors not found")

        # Find an actor file
        actor_files = list(actors_dir.glob("*.md"))
        if not actor_files:
            pytest.skip("No actor files found")

        actor_file = actor_files[0]
        actor = PersonEntry.load(actor_file)

        assert actor.id is not None
        assert actor.title is not None
        assert actor.entry_type == "person"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
