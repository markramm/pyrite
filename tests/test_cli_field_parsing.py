"""Tests for CLI --field value parsing."""

import pytest

from pyrite.cli.entry_commands import _parse_field_value


class TestParseFieldValue:
    """Test _parse_field_value handles various input formats."""

    # --- JSON arrays and objects ---

    def test_json_array(self):
        assert _parse_field_value('[1, 2, 3]') == [1, 2, 3]

    def test_json_string_array(self):
        assert _parse_field_value('["ICE", "Adelanto"]') == ["ICE", "Adelanto"]

    def test_json_object(self):
        result = _parse_field_value('{"url": "https://example.com", "title": "Test"}')
        assert result == {"url": "https://example.com", "title": "Test"}

    def test_json_array_of_objects(self):
        result = _parse_field_value('[{"url": "https://example.com", "tier": 1}]')
        assert isinstance(result, list)
        assert result[0]["url"] == "https://example.com"
        assert result[0]["tier"] == 1

    def test_invalid_json_falls_through(self):
        """Malformed JSON starting with [ should fall through to comma-split."""
        result = _parse_field_value("[not valid json")
        # Falls through to comma-separated since it contains no comma -> plain string
        assert result == "[not valid json"

    # --- Integers ---

    def test_integer(self):
        assert _parse_field_value("42") == 42

    def test_negative_integer(self):
        assert _parse_field_value("-5") == -5

    def test_zero(self):
        assert _parse_field_value("0") == 0

    # --- Floats ---

    def test_float(self):
        assert _parse_field_value("3.14") == pytest.approx(3.14)

    # --- Booleans ---

    def test_true(self):
        assert _parse_field_value("true") is True

    def test_false(self):
        assert _parse_field_value("false") is False

    def test_true_case_insensitive(self):
        assert _parse_field_value("True") is True

    # --- Comma-separated lists ---

    def test_comma_separated(self):
        assert _parse_field_value("ICE,Adelanto") == ["ICE", "Adelanto"]

    def test_comma_separated_with_spaces(self):
        assert _parse_field_value("ICE, Adelanto, CBP") == ["ICE", "Adelanto", "CBP"]

    def test_trailing_comma_ignored(self):
        result = _parse_field_value("a,b,")
        assert result == ["a", "b"]

    # --- Plain strings ---

    def test_plain_string(self):
        assert _parse_field_value("confirmed") == "confirmed"

    def test_string_with_spaces(self):
        assert _parse_field_value("some value") == "some value"

    def test_empty_string(self):
        assert _parse_field_value("") == ""


class TestParseFieldValueEndToEnd:
    """Test that parsed values survive through build_entry for known types."""

    def test_participants_comma_list_creates_event(self):
        """Comma-separated participants should create an EventEntry with a list."""
        from pyrite.models.factory import build_entry

        entry = build_entry(
            "event",
            title="Test Event",
            body="test",
            date="2026-03-30",
            participants=_parse_field_value("ICE,Adelanto,CBP"),
        )
        assert entry.participants == ["ICE", "Adelanto", "CBP"]

    def test_sources_json_creates_event(self):
        """JSON array sources should create an EventEntry with parsed sources."""
        from pyrite.models.factory import build_entry

        entry = build_entry(
            "event",
            title="Test Event",
            body="test",
            date="2026-03-30",
            sources=_parse_field_value('[{"url": "https://example.com", "title": "Source"}]'),
        )
        assert len(entry.sources) == 1
        assert entry.sources[0].url == "https://example.com"

    def test_importance_integer(self):
        """Integer importance should be parsed correctly."""
        from pyrite.models.factory import build_entry

        entry = build_entry(
            "event",
            title="Test Event",
            body="test",
            importance=_parse_field_value("8"),
        )
        assert entry.importance == 8

    def test_status_string_preserved(self):
        """Valid EventStatus string should pass through correctly."""
        from pyrite.models.factory import build_entry

        entry = build_entry(
            "event",
            title="Test Event",
            body="test",
            status=_parse_field_value("disputed"),
        )
        assert entry.status.value == "disputed"
