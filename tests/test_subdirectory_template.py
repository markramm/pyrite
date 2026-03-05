"""Tests for subdirectory template expansion."""

import tempfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import pytest

from pyrite.config import KBConfig
from pyrite.schema.field_schema import TypeSchema, expand_subdirectory_template
from pyrite.schema.kb_schema import KBSchema
from pyrite.storage.repository import KBRepository


# --- Helpers ---


class MockStatus(StrEnum):
    ACTIVE = "active"
    DONE = "done"


@dataclass
class MockEntry:
    """Minimal entry-like object for testing template expansion."""

    id: str = "test-entry"
    entry_type: str = "note"
    status: str = "active"
    metadata: dict = field(default_factory=dict)


@dataclass
class MockEnumEntry:
    """Entry with an enum field."""

    id: str = "test-entry"
    entry_type: str = "event"
    status: MockStatus = MockStatus.ACTIVE
    metadata: dict = field(default_factory=dict)


@dataclass
class MockMetadataEntry:
    """Entry that stores fields in metadata (like GenericEntry)."""

    id: str = "test-entry"
    entry_type: str = "custom"
    metadata: dict = field(default_factory=dict)


# --- expand_subdirectory_template ---


class TestExpandSubdirectoryTemplate:
    def test_plain_string_passthrough(self):
        """Plain string without braces returns unchanged."""
        entry = MockEntry()
        assert expand_subdirectory_template("backlog", entry) == "backlog"

    def test_single_field_expansion(self):
        """Single {field} placeholder expands from entry attribute."""
        entry = MockEntry(status="done")
        assert expand_subdirectory_template("backlog/{status}", entry) == "backlog/done"

    def test_multiple_field_expansion(self):
        """Multiple placeholders expand independently."""
        entry = MockEntry(status="active")
        entry.priority = "high"
        assert (
            expand_subdirectory_template("{entry_type}/{status}", entry)
            == "note/active"
        )

    def test_enum_field_expansion(self):
        """Enum fields use .value for expansion."""
        entry = MockEnumEntry(status=MockStatus.DONE)
        assert expand_subdirectory_template("items/{status}", entry) == "items/done"

    def test_metadata_field_resolution(self):
        """Fields not found as attributes fall back to metadata."""
        entry = MockMetadataEntry(metadata={"category": "reference"})
        assert (
            expand_subdirectory_template("docs/{category}", entry) == "docs/reference"
        )

    def test_missing_field_fallback(self):
        """Missing fields resolve to '_unknown'."""
        entry = MockEntry()
        assert (
            expand_subdirectory_template("items/{nonexistent}", entry)
            == "items/_unknown"
        )

    def test_path_traversal_sanitized(self):
        """Path traversal attempts are neutralized."""
        entry = MockEntry(status="../etc/passwd")
        result = expand_subdirectory_template("items/{status}", entry)
        assert ".." not in result
        assert result.startswith("items/")

    def test_spaces_and_case_normalized(self):
        """Spaces become hyphens, values lowercased."""
        entry = MockEntry(status="In Progress")
        assert (
            expand_subdirectory_template("items/{status}", entry)
            == "items/in-progress"
        )

    def test_empty_template(self):
        """Empty string returns empty string."""
        entry = MockEntry()
        assert expand_subdirectory_template("", entry) == ""

    def test_leading_slash_stripped(self):
        """Leading slashes in result are stripped."""
        entry = MockEntry(status="/bad")
        result = expand_subdirectory_template("/{status}", entry)
        assert not result.startswith("/")


# --- TypeSchema.resolve_subdirectory ---


class TestTypeSchemaResolveSubdirectory:
    def test_resolve_static(self):
        """Static subdirectory returned unchanged."""
        ts = TypeSchema(name="note", subdirectory="notes")
        entry = MockEntry()
        assert ts.resolve_subdirectory(entry) == "notes"

    def test_resolve_template(self):
        """Template subdirectory expanded from entry."""
        ts = TypeSchema(name="backlog_item", subdirectory="backlog/{status}")
        entry = MockEntry(status="done")
        assert ts.resolve_subdirectory(entry) == "backlog/done"

    def test_resolve_empty(self):
        """Empty subdirectory returns empty string."""
        ts = TypeSchema(name="note", subdirectory="")
        entry = MockEntry()
        assert ts.resolve_subdirectory(entry) == ""


# --- Repository integration ---


class TestInferSubdirWithTemplates:
    @pytest.fixture
    def kb_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def _make_repo_with_schema(self, kb_dir, types_dict):
        """Helper: create a KBConfig with a KBSchema injected into the cache."""
        schema = KBSchema(types=types_dict)
        config = KBConfig(path=kb_dir, name="test", kb_type="generic")
        config._schema_cache = schema
        return KBRepository(config)

    def test_infer_subdir_expands_template(self, kb_dir):
        """_infer_subdir() expands template placeholders from TypeSchema."""
        repo = self._make_repo_with_schema(kb_dir, {
            "backlog_item": TypeSchema(
                name="backlog_item", subdirectory="backlog/{status}"
            )
        })
        entry = MockEntry(entry_type="backlog_item", status="done")
        assert repo._infer_subdir(entry) == "backlog/done"

    def test_infer_subdir_static_backward_compat(self, kb_dir):
        """Static subdirectory (no template) still works unchanged."""
        repo = self._make_repo_with_schema(kb_dir, {
            "adr": TypeSchema(name="adr", subdirectory="adrs")
        })
        entry = MockEntry(entry_type="adr")
        assert repo._infer_subdir(entry) == "adrs"

    def test_find_file_nested(self, kb_dir):
        """find_file() finds entries in nested template subdirectories."""
        # Create a file at depth 2: backlog/done/my-item.md
        nested = kb_dir / "backlog" / "done"
        nested.mkdir(parents=True)
        (nested / "my-item.md").write_text("---\ntitle: test\n---\n")

        config = KBConfig(path=kb_dir, name="test", kb_type="generic")
        repo = KBRepository(config)
        result = repo.find_file("my-item")
        assert result is not None
        assert result.resolve() == (nested / "my-item.md").resolve()
