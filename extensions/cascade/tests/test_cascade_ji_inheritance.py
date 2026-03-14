"""Tests for Cascade entry type inheritance from journalism-investigation base types."""

import pytest

from pyrite_cascade.entry_types import TimelineEventEntry
from pyrite_journalism_investigation.entry_types import InvestigationEventEntry
from pyrite.models.core_types import EventEntry


class TestTimelineEventInheritance:
    """TimelineEventEntry should extend InvestigationEventEntry."""

    def test_is_subclass_of_investigation_event(self):
        assert issubclass(TimelineEventEntry, InvestigationEventEntry)

    def test_is_subclass_of_event_entry(self):
        """Still an EventEntry through the chain."""
        assert issubclass(TimelineEventEntry, EventEntry)

    def test_entry_type_returns_timeline_event(self):
        """entry_type must still return 'timeline_event', not 'investigation_event'."""
        entry = TimelineEventEntry(
            id="te-001", title="Test Event", body=""
        )
        assert entry.entry_type == "timeline_event"


class TestTimelineEventBackwardCompat:
    """Existing frontmatter without JI fields must still load correctly."""

    def test_load_without_ji_fields(self):
        """Frontmatter without source_refs/verification_status loads with defaults."""
        meta = {
            "id": "te-001",
            "title": "Old Timeline Event",
            "type": "timeline_event",
            "date": "1995-01-15",
            "actors": ["actor-a", "actor-b"],
            "capture_lanes": ["financial"],
            "capture_type": "regulatory",
            "connections": ["conn-1"],
            "patterns": ["pattern-1"],
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "Body text")

        assert entry.id == "te-001"
        assert entry.title == "Old Timeline Event"
        assert entry.date == "1995-01-15"
        assert entry.actors == ["actor-a", "actor-b"]
        assert entry.capture_lanes == ["financial"]
        assert entry.capture_type == "regulatory"
        assert entry.connections == ["conn-1"]
        assert entry.patterns == ["pattern-1"]
        # JI defaults
        assert entry.source_refs == []
        assert entry.verification_status == "unverified"

    def test_cascade_fields_preserved_in_roundtrip(self):
        """All Cascade-specific fields survive to_frontmatter -> from_frontmatter."""
        meta = {
            "id": "te-002",
            "title": "Roundtrip Event",
            "date": "2000-03-01",
            "capture_lanes": ["political", "financial"],
            "actors": ["actor-x"],
            "capture_type": "privatization",
            "connections": ["conn-a", "conn-b"],
            "patterns": ["pattern-z"],
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "Body")
        fm = entry.to_frontmatter()

        assert fm["capture_lanes"] == ["political", "financial"]
        assert fm["actors"] == ["actor-x"]
        assert fm["capture_type"] == "privatization"
        assert fm["connections"] == ["conn-a", "conn-b"]
        assert fm["patterns"] == ["pattern-z"]

    def test_actors_field_works_as_list_of_strings(self):
        entry = TimelineEventEntry(
            id="te-003", title="Test", body="",
            actors=["actor-1", "actor-2"],
        )
        assert entry.actors == ["actor-1", "actor-2"]


class TestTimelineEventJIFields:
    """New JI-inherited fields (source_refs, verification_status) work correctly."""

    def test_source_refs_roundtrip(self):
        meta = {
            "id": "te-010",
            "title": "Sourced Event",
            "date": "1998-06-01",
            "source_refs": ["src-1", "src-2"],
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "")
        assert entry.source_refs == ["src-1", "src-2"]

        fm = entry.to_frontmatter()
        assert fm["source_refs"] == ["src-1", "src-2"]

    def test_verification_status_roundtrip(self):
        meta = {
            "id": "te-011",
            "title": "Verified Event",
            "date": "1998-06-01",
            "verification_status": "verified",
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "")
        assert entry.verification_status == "verified"

        fm = entry.to_frontmatter()
        assert fm["verification_status"] == "verified"

    def test_verification_status_default_not_in_frontmatter(self):
        """When verification_status is default ('unverified'), it should not appear in frontmatter."""
        meta = {
            "id": "te-012",
            "title": "Unverified Event",
            "date": "1998-06-01",
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "")
        fm = entry.to_frontmatter()
        assert "verification_status" not in fm

    def test_empty_source_refs_not_in_frontmatter(self):
        """Empty source_refs should not appear in frontmatter."""
        meta = {
            "id": "te-013",
            "title": "No Sources Event",
            "date": "1998-06-01",
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "")
        fm = entry.to_frontmatter()
        assert "source_refs" not in fm

    def test_full_roundtrip_with_all_fields(self):
        """All fields — Cascade-specific and JI-inherited — survive a full roundtrip."""
        meta = {
            "id": "te-020",
            "title": "Full Event",
            "date": "2001-09-15",
            "location": "Moscow",
            "importance": 8,
            "capture_lanes": ["financial", "political"],
            "actors": ["actor-a"],
            "capture_type": "privatization",
            "connections": ["conn-1"],
            "patterns": ["pattern-1"],
            "source_refs": ["src-a", "src-b"],
            "verification_status": "partially_verified",
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "Full body")
        fm = entry.to_frontmatter()

        entry2 = TimelineEventEntry.from_frontmatter(fm, "Full body")
        assert entry2.capture_lanes == ["financial", "political"]
        assert entry2.actors == ["actor-a"]
        assert entry2.capture_type == "privatization"
        assert entry2.connections == ["conn-1"]
        assert entry2.patterns == ["pattern-1"]
        assert entry2.source_refs == ["src-a", "src-b"]
        assert entry2.verification_status == "partially_verified"
        assert entry2.location == "Moscow"
        assert entry2.importance == 8
