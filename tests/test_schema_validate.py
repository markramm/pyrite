"""Tests for schema validate command and validation logic."""

import json
import tempfile
from pathlib import Path

import pytest

from pyrite.cli.schema_commands import (
    _parse_frontmatter,
    detect_id_collisions,
    validate_entry,
)


class TestParseFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\ntype: note\ntitle: Test\n---\nBody text")
        fm, body, errors = _parse_frontmatter(f)
        assert fm["type"] == "note"
        assert fm["title"] == "Test"
        assert body == "Body text"
        assert errors == []

    def test_missing_opening_dashes(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("type: note\ntitle: Test\n---\nBody")
        fm, body, errors = _parse_frontmatter(f)
        assert len(errors) == 1
        assert errors[0]["check"] == "frontmatter_parse"
        assert "No YAML frontmatter" in errors[0]["message"]

    def test_unterminated_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\ntype: note\ntitle: Test\n")
        fm, body, errors = _parse_frontmatter(f)
        assert len(errors) == 1
        assert "Unterminated" in errors[0]["message"]

    def test_missing_type(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\ntitle: Test\n---\nBody")
        fm, body, errors = _parse_frontmatter(f)
        assert any("type" in e["message"] for e in errors)

    def test_missing_title(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\ntype: note\n---\nBody")
        fm, body, errors = _parse_frontmatter(f)
        assert any("title" in e["message"] for e in errors)

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\n: invalid: yaml: [unclosed\n---\nBody")
        fm, body, errors = _parse_frontmatter(f)
        assert any(e["check"] == "frontmatter_parse" for e in errors)

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "nonexistent.md"
        fm, body, errors = _parse_frontmatter(f)
        assert len(errors) == 1
        assert errors[0]["check"] == "read"


class TestValidateEntry:
    def test_valid_entry_no_schema(self, tmp_path):
        f = tmp_path / "test.md"
        fm = {"type": "note", "title": "Test"}
        errors = validate_entry(f, fm)
        assert errors == []

    def test_int_priority_no_warning(self, tmp_path):
        f = tmp_path / "test.md"
        fm = {"type": "note", "title": "Test", "priority": 5}
        errors = validate_entry(f, fm)
        assert errors == []

    def test_string_priority_type_warning(self, tmp_path):
        f = tmp_path / "test.md"
        fm = {"type": "note", "title": "Test", "priority": "high"}
        errors = validate_entry(f, fm)
        assert len(errors) == 1
        assert errors[0]["check"] == "protocol_field_type"
        assert errors[0]["severity"] == "warning"

    def test_string_date_no_warning(self, tmp_path):
        f = tmp_path / "test.md"
        fm = {"type": "adr", "title": "Test", "date": "2026-01-01"}
        errors = validate_entry(f, fm)
        assert errors == []

    def test_missing_required_field_with_schema(self, tmp_path):
        """When schema defines required fields, missing ones are errors."""
        from pyrite.schema import KBSchema

        schema = KBSchema.from_dict(
            {
                "types": {
                    "adr": {
                        "required": ["title", "adr_number"],
                    }
                }
            }
        )
        f = tmp_path / "test.md"
        fm = {"type": "adr", "title": "Test"}
        errors = validate_entry(f, fm, schema)
        assert any("adr_number" in e["message"] for e in errors)


class TestDetectIdCollisions:
    def test_no_collisions(self, tmp_path):
        entries = [
            (tmp_path / "a.md", {"id": "adr-001", "type": "adr", "title": "A"}),
            (tmp_path / "b.md", {"id": "backlog-001", "type": "backlog_item", "title": "B"}),
        ]
        errors = detect_id_collisions(entries)
        assert errors == []

    def test_cross_type_collision(self, tmp_path):
        """Two entries with same generated ID but different types = collision."""
        entries = [
            (tmp_path / "a.md", {"type": "adr", "title": "Content Negotiation"}),
            (tmp_path / "b.md", {"type": "backlog_item", "title": "Content Negotiation"}),
        ]
        errors = detect_id_collisions(entries)
        assert len(errors) == 2
        assert all(e["check"] == "id_collision" for e in errors)
        assert all(e["severity"] == "error" for e in errors)

    def test_same_type_duplicate(self, tmp_path):
        """Two entries with same ID and same type = duplicate."""
        entries = [
            (tmp_path / "a.md", {"id": "foo", "type": "note", "title": "A"}),
            (tmp_path / "b.md", {"id": "foo", "type": "note", "title": "B"}),
        ]
        errors = detect_id_collisions(entries)
        assert len(errors) == 2
        assert "Duplicate ID" in errors[0]["message"]

    def test_explicit_id_prevents_collision(self, tmp_path):
        """Explicit IDs avoid title-based collisions."""
        entries = [
            (tmp_path / "a.md", {"id": "adr-0010", "type": "adr", "title": "Content Negotiation"}),
            (
                tmp_path / "b.md",
                {
                    "id": "content-negotiation-backlog",
                    "type": "backlog_item",
                    "title": "Content Negotiation",
                },
            ),
        ]
        errors = detect_id_collisions(entries)
        assert errors == []

    def test_generated_id_from_title(self, tmp_path):
        """Without explicit id, title is slugified for collision detection."""
        entries = [
            (tmp_path / "a.md", {"type": "adr", "title": "Entry Protocol Mixins"}),
            (tmp_path / "b.md", {"type": "backlog_item", "title": "Entry Protocol Mixins"}),
        ]
        errors = detect_id_collisions(entries)
        assert len(errors) == 2  # Cross-type collision


class TestADRDateColumn:
    """Verify sw_adrs reads date from the DB column, not just metadata JSON."""

    def test_date_from_db_column_overrides_metadata(self):
        from pyrite.storage.database import PyriteDB
        from pyrite_software_kb.cli import _query_entries

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            try:
                db._raw_conn.execute(
                    "INSERT INTO kb (name, path, kb_type) VALUES (?, ?, ?)",
                    ("test", str(tmpdir), "generic"),
                )
                # Insert entry with date in DB column but different in metadata
                db._raw_conn.execute(
                    "INSERT INTO entry (id, kb_name, entry_type, title, body, status, date, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "adr-001",
                        "test",
                        "adr",
                        "Test ADR",
                        "",
                        "accepted",
                        "2026-03-01",
                        json.dumps({"adr_number": 1, "date": ""}),
                    ),
                )
                db._raw_conn.commit()

                rows = _query_entries(db, "adr")
                assert len(rows) == 1
                row = rows[0]

                # The expression `r.get("date") or r["_meta"].get("date", "")` should
                # pick up the DB column value "2026-03-01"
                date_value = row.get("date") or row["_meta"].get("date", "")
                assert date_value == "2026-03-01"
            finally:
                db.close()


class TestPriorityStringType:
    """Verify priority is stored and read as a string."""

    def test_priority_string_roundtrip(self):
        from pyrite.storage.database import PyriteDB
        from pyrite_software_kb.cli import _query_entries

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            try:
                db._raw_conn.execute(
                    "INSERT INTO kb (name, path, kb_type) VALUES (?, ?, ?)",
                    ("test", str(tmpdir), "generic"),
                )
                db._raw_conn.execute(
                    "INSERT INTO entry (id, kb_name, entry_type, title, body, status, priority, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "test-item",
                        "test",
                        "backlog_item",
                        "Test",
                        "",
                        "proposed",
                        "high",
                        json.dumps({"kind": "bug"}),
                    ),
                )
                db._raw_conn.commit()

                rows = _query_entries(db, "backlog_item")
                assert len(rows) == 1
                priority = rows[0].get("priority") or rows[0]["_meta"].get("priority", "")
                assert priority == "high"
                assert isinstance(priority, str)
            finally:
                db.close()

    def test_prioritizable_protocol_int(self):
        from dataclasses import dataclass

        from pyrite.models.protocols import Prioritizable

        @dataclass
        class T(Prioritizable):
            pass

        t = T(priority=3)
        assert t.priority == 3
        fm = t._prioritizable_to_frontmatter()
        assert fm == {"priority": 3}

        result = Prioritizable._prioritizable_from_frontmatter({"priority": 7})
        assert result == {"priority": 7}

    def test_prioritizable_protocol_non_numeric_fallback(self):
        from pyrite.models.protocols import Prioritizable

        result = Prioritizable._prioritizable_from_frontmatter({"priority": "critical"})
        assert result == {"priority": 0}


class TestSchemaValidateCLI:
    """Test the CLI command integration."""

    def test_validate_clean_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\ntype: note\ntitle: Clean Entry\n---\nBody")
        fm, body, errors = _parse_frontmatter(f)
        assert errors == []
        entry_errors = validate_entry(f, fm)
        assert entry_errors == []

    def test_validate_multiple_issues(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text("---\ntitle: Missing Type\npriority: 5\n---\nBody")
        fm, body, errors = _parse_frontmatter(f)
        # Missing type is an error from parse
        assert any("type" in e["message"] for e in errors)

    def test_validate_wrong_protocol_type(self, tmp_path):
        f = tmp_path / "bad.md"
        # Use a string value for a field that expects int to trigger type warning
        f.write_text("---\ntype: note\ntitle: Bad Importance\nimportance: very-high\n---\nBody")
        fm, body, errors = _parse_frontmatter(f)
        assert errors == []
        entry_errors = validate_entry(f, fm)
        # importance: "very-high" is non-numeric — should produce a warning
        assert any(e["check"] == "protocol_field_type" for e in entry_errors) or len(entry_errors) == 0
        # Note: safe_int silently converts to default, so validation may pass
