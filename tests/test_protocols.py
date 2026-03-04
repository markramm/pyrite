"""Tests for entry protocol mixins."""

from dataclasses import dataclass

import pytest

from pyrite.models.protocols import (
    PROTOCOL_FIELDS,
    PROTOCOL_REGISTRY,
    Assignable,
    Locatable,
    Prioritizable,
    Statusable,
    Temporal,
)


class TestAssignable:
    def test_defaults(self):
        @dataclass
        class T(Assignable):
            pass

        t = T()
        assert t.assignee == ""
        assert t.assigned_at == ""

    def test_to_frontmatter_empty(self):
        @dataclass
        class T(Assignable):
            pass

        t = T()
        assert t._assignable_to_frontmatter() == {}

    def test_to_frontmatter_with_values(self):
        @dataclass
        class T(Assignable):
            pass

        t = T(assignee="alice", assigned_at="2026-03-01T00:00:00Z")
        fm = t._assignable_to_frontmatter()
        assert fm == {"assignee": "alice", "assigned_at": "2026-03-01T00:00:00Z"}

    def test_from_frontmatter(self):
        result = Assignable._assignable_from_frontmatter(
            {"assignee": "bob", "assigned_at": "2026-01-01"}
        )
        assert result == {"assignee": "bob", "assigned_at": "2026-01-01"}

    def test_from_frontmatter_missing(self):
        result = Assignable._assignable_from_frontmatter({})
        assert result == {"assignee": "", "assigned_at": ""}


class TestTemporal:
    def test_defaults(self):
        @dataclass
        class T(Temporal):
            pass

        t = T()
        assert t.date == ""
        assert t.start_date == ""
        assert t.end_date == ""
        assert t.due_date == ""

    def test_to_frontmatter_partial(self):
        @dataclass
        class T(Temporal):
            pass

        t = T(date="2026-03-01", due_date="2026-04-01")
        fm = t._temporal_to_frontmatter()
        assert fm == {"date": "2026-03-01", "due_date": "2026-04-01"}
        assert "start_date" not in fm
        assert "end_date" not in fm

    def test_from_frontmatter(self):
        result = Temporal._temporal_from_frontmatter(
            {"date": "2026-01-01", "start_date": "2026-01-01", "end_date": "2026-12-31", "due_date": "2026-06-01"}
        )
        assert result == {
            "date": "2026-01-01",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "due_date": "2026-06-01",
        }


class TestLocatable:
    def test_defaults(self):
        @dataclass
        class T(Locatable):
            pass

        t = T()
        assert t.location == ""
        assert t.coordinates == ""

    def test_to_frontmatter(self):
        @dataclass
        class T(Locatable):
            pass

        t = T(location="NYC", coordinates="40.7,-74.0")
        fm = t._locatable_to_frontmatter()
        assert fm == {"location": "NYC", "coordinates": "40.7,-74.0"}

    def test_from_frontmatter(self):
        result = Locatable._locatable_from_frontmatter({"location": "London"})
        assert result == {"location": "London", "coordinates": ""}


class TestStatusable:
    def test_defaults(self):
        @dataclass
        class T(Statusable):
            pass

        t = T()
        assert t.status == ""

    def test_to_frontmatter(self):
        @dataclass
        class T(Statusable):
            pass

        t = T(status="active")
        assert t._statusable_to_frontmatter() == {"status": "active"}

    def test_to_frontmatter_empty(self):
        @dataclass
        class T(Statusable):
            pass

        t = T()
        assert t._statusable_to_frontmatter() == {}


class TestPrioritizable:
    def test_defaults(self):
        @dataclass
        class T(Prioritizable):
            pass

        t = T()
        assert t.priority == ""

    def test_to_frontmatter(self):
        @dataclass
        class T(Prioritizable):
            pass

        t = T(priority="high")
        assert t._prioritizable_to_frontmatter() == {"priority": "high"}

    def test_to_frontmatter_empty(self):
        @dataclass
        class T(Prioritizable):
            pass

        t = T()
        assert t._prioritizable_to_frontmatter() == {}

    def test_from_frontmatter(self):
        result = Prioritizable._prioritizable_from_frontmatter({"priority": "high"})
        assert result == {"priority": "high"}


class TestMixinComposition:
    """Test that multiple mixins compose without MRO conflicts."""

    def test_two_mixins(self):
        @dataclass
        class TaskLike(Assignable, Statusable):
            name: str = ""

        t = TaskLike(assignee="alice", status="open", name="Test")
        assert t.assignee == "alice"
        assert t.status == "open"
        assert t.name == "Test"

    def test_all_five_mixins(self):
        @dataclass
        class SuperEntry(Assignable, Temporal, Locatable, Statusable, Prioritizable):
            title: str = ""

        s = SuperEntry(
            assignee="bob",
            date="2026-01-01",
            location="NYC",
            status="active",
            priority="high",
            title="Test",
        )
        assert s.assignee == "bob"
        assert s.date == "2026-01-01"
        assert s.location == "NYC"
        assert s.status == "active"
        assert s.priority == "high"
        assert s.title == "Test"

    def test_composed_frontmatter_helpers(self):
        @dataclass
        class TaskLike(Assignable, Temporal, Prioritizable):
            pass

        t = TaskLike(assignee="alice", due_date="2026-04-01", priority="high")
        fm = {}
        fm.update(t._assignable_to_frontmatter())
        fm.update(t._temporal_to_frontmatter())
        fm.update(t._prioritizable_to_frontmatter())
        assert fm == {"assignee": "alice", "due_date": "2026-04-01", "priority": "high"}

    def test_mro_no_conflict(self):
        """All 5 protocols can be combined in any order."""

        @dataclass
        class Order1(Assignable, Temporal, Locatable, Statusable, Prioritizable):
            pass

        @dataclass
        class Order2(Prioritizable, Statusable, Locatable, Temporal, Assignable):
            pass

        # Both should instantiate without error
        Order1()
        Order2()


class TestProtocolRegistry:
    def test_all_protocols_registered(self):
        assert "assignable" in PROTOCOL_REGISTRY
        assert "temporal" in PROTOCOL_REGISTRY
        assert "locatable" in PROTOCOL_REGISTRY
        assert "statusable" in PROTOCOL_REGISTRY
        assert "prioritizable" in PROTOCOL_REGISTRY
        assert len(PROTOCOL_REGISTRY) == 5

    def test_field_mapping(self):
        assert PROTOCOL_FIELDS["assignee"] is Assignable
        assert PROTOCOL_FIELDS["date"] is Temporal
        assert PROTOCOL_FIELDS["due_date"] is Temporal
        assert PROTOCOL_FIELDS["location"] is Locatable
        assert PROTOCOL_FIELDS["coordinates"] is Locatable
        assert PROTOCOL_FIELDS["status"] is Statusable
        assert PROTOCOL_FIELDS["priority"] is Prioritizable


class TestImportancePromotion:
    """Test that importance was promoted to base Entry."""

    def test_base_entry_has_importance(self):
        from pyrite.models.base import Entry

        import dataclasses
        field_names = {f.name for f in dataclasses.fields(Entry)}
        assert "importance" in field_names

    def test_note_entry_inherits_importance(self):
        from pyrite.models.core_types import NoteEntry

        note = NoteEntry(id="test", title="Test", importance=8)
        assert note.importance == 8
        fm = note.to_frontmatter()
        assert fm["importance"] == 8

    def test_note_entry_default_importance_omitted(self):
        from pyrite.models.core_types import NoteEntry

        note = NoteEntry(id="test", title="Test")
        assert note.importance == 5
        fm = note.to_frontmatter()
        assert "importance" not in fm

    def test_event_entry_importance(self):
        from pyrite.models.core_types import EventEntry

        event = EventEntry(id="2026-03-01--test", title="Test", date="2026-03-01", importance=7)
        assert event.importance == 7
        fm = event.to_frontmatter()
        assert fm["importance"] == 7

    def test_importance_roundtrip(self):
        from pyrite.models.core_types import PersonEntry

        person = PersonEntry(id="test", title="Test", importance=3)
        fm = person.to_frontmatter()
        restored = PersonEntry.from_frontmatter(fm, "")
        assert restored.importance == 3
