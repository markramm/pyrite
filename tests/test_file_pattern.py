"""Tests for file_pattern support in TypeSchema and KBRepository."""

import pytest

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

        schema = KBSchema.from_dict(
            {
                "name": "test",
                "types": {
                    "event": {
                        "description": "An event",
                        "file_pattern": "{date}--{slug}.md",
                    }
                },
            }
        )
        ts = schema.get_type_schema("event")
        assert ts is not None
        assert ts.file_pattern == "{date}--{slug}.md"


class TestResolveFilenameEntryFieldPlaceholders:
    """#391: `resolve_filename` gains the entry's OWN fields as placeholders
    (not just the fixed id/slug/date/title/type set), with Python format
    specs, e.g. ``{adr_number:04d}-{title}.md`` -- what the software-kb
    `adr` type declares to keep its ``NNNN-slug.md`` convention through
    `KBService.create`.
    """

    def _adr_entry(self, **kwargs):
        from pyrite_software_kb.entry_types import ADREntry

        defaults = {"id": "adr-0007", "title": "Use PostgreSQL"}
        defaults.update(kwargs)
        return ADREntry(**defaults)

    def test_entry_field_placeholder_with_format_spec(self):
        schema = TypeSchema(name="adr", file_pattern="{adr_number:04d}-{title}.md")
        entry = self._adr_entry(adr_number=7)
        assert schema.resolve_filename(entry) == "0007-use-postgresql.md"

    def test_entry_field_placeholder_without_format_spec(self):
        schema = TypeSchema(name="adr", file_pattern="adr-{adr_number}.md")
        entry = self._adr_entry(adr_number=7)
        assert schema.resolve_filename(entry) == "adr-7.md"

    def test_missing_field_is_refused_with_a_clear_error(self):
        """A placeholder naming a field the entry does not have is refused,
        not silently dropped -- an ADR without its number must not land at
        a filename nobody can find (e.g. `-use-postgresql.md`)."""
        from pyrite.exceptions import ValidationError

        schema = TypeSchema(name="adr", file_pattern="{does_not_exist:04d}-{title}.md")
        entry = self._adr_entry(adr_number=7)
        with pytest.raises(ValidationError, match="does_not_exist"):
            schema.resolve_filename(entry)

    def test_traversal_attempt_is_refused(self):
        """A field value containing a path separator or `..` must not reach
        the filename -- it would let entry data escape the type's folder.
        `superseded_by` is a plain free-text field on ADREntry, unlike
        `{title}`/`{slug}`, which are already slugified before this check."""
        from pyrite.exceptions import ValidationError

        schema = TypeSchema(name="adr", file_pattern="{superseded_by}.md")
        entry = self._adr_entry(superseded_by="../../etc/passwd")
        with pytest.raises(ValidationError, match="path"):
            schema.resolve_filename(entry)

    def test_traversal_attempt_via_dotdot_in_field_value(self):
        from pyrite.exceptions import ValidationError

        schema = TypeSchema(name="adr", file_pattern="{slug}.md")
        entry = self._adr_entry(id="..")
        with pytest.raises(ValidationError):
            schema.resolve_filename(entry)

    def test_existing_placeholders_keep_working(self):
        """id/slug/date/title/type must still resolve after adding entry-field
        placeholder support -- this is a regression guard, not new behaviour."""
        from pyrite.models.factory import build_entry

        schema = TypeSchema(name="event", file_pattern="{date}--{slug}.md")
        entry = build_entry("event", title="ICE Raid Downtown", body="", date="2026-03-30")
        assert schema.resolve_filename(entry) == "2026-03-30--ice-raid-downtown.md"
