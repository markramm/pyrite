"""Tests for file_pattern support in TypeSchema and KBRepository."""

from pyrite.schema.field_schema import TypeSchema


class TestTypeSchemaFilePattern:
    """Test TypeSchema.resolve_filename with file_pattern."""

    def test_no_pattern_returns_none(self):
        schema = TypeSchema(name="event")
        from pyrite.models.factory import build_entry

        entry = build_entry("event", title="Test Event", body="", date="2026-03-30")
        assert schema.resolve_filename(entry) is None

    def test_date_slug_pattern(self):
        schema = TypeSchema(name="event", file_pattern="{date}--{slug}.md")
        from pyrite.models.factory import build_entry

        entry = build_entry("event", title="ICE Raid Downtown", body="", date="2026-03-30")
        result = schema.resolve_filename(entry)
        assert result == "2026-03-30--ice-raid-downtown.md"

    def test_date_only_pattern(self):
        schema = TypeSchema(name="event", file_pattern="{date}.md")
        from pyrite.models.factory import build_entry

        entry = build_entry("event", title="Something", body="", date="2026-01-15")
        result = schema.resolve_filename(entry)
        assert result == "2026-01-15.md"

    def test_id_pattern(self):
        schema = TypeSchema(name="note", file_pattern="{id}.md")
        from pyrite.models.factory import build_entry

        entry = build_entry("note", entry_id="my-note", title="My Note", body="")
        result = schema.resolve_filename(entry)
        assert result == "my-note.md"

    def test_type_in_pattern(self):
        schema = TypeSchema(name="event", file_pattern="{type}--{date}--{slug}.md")
        from pyrite.models.factory import build_entry

        entry = build_entry("event", title="Test", body="", date="2026-03-30")
        result = schema.resolve_filename(entry)
        assert result == "event--2026-03-30--test.md"

    def test_missing_date_uses_empty_string(self):
        schema = TypeSchema(name="note", file_pattern="{date}--{slug}.md")
        from pyrite.models.factory import build_entry

        entry = build_entry("note", title="No Date Note", body="")
        result = schema.resolve_filename(entry)
        assert result == "--no-date-note.md"

    def test_to_dict_includes_file_pattern(self):
        schema = TypeSchema(name="event", file_pattern="{date}--{slug}.md")
        d = schema.to_dict()
        assert d["file_pattern"] == "{date}--{slug}.md"

    def test_to_dict_omits_empty_file_pattern(self):
        schema = TypeSchema(name="event")
        d = schema.to_dict()
        assert "file_pattern" not in d


class TestKBSchemaLoadsFilePattern:
    """Test that file_pattern is loaded from kb.yaml-style dicts."""

    def test_loads_file_pattern(self):
        from pyrite.schema.kb_schema import KBSchema

        schema = KBSchema.from_dict({
            "name": "test",
            "types": {
                "event": {
                    "description": "An event",
                    "file_pattern": "{date}--{slug}.md",
                }
            },
        })
        ts = schema.get_type_schema("event")
        assert ts is not None
        assert ts.file_pattern == "{date}--{slug}.md"
