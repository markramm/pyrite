"""Tests for NotebookLM renderer and bundler."""

import pytest

from pyrite.models.core_types import (
    DocumentEntry,
    EventEntry,
    NoteEntry,
    OrganizationEntry,
    PersonEntry,
    RelationshipEntry,
)
from pyrite.renderers.notebooklm import (
    BundleStrategy,
    SourceMode,
    bundle_entries,
    generate_manifest,
    render_entry,
)
from pyrite.schema import Link, Source


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_note():
    return NoteEntry(id="my-note", title="My Note", body="Some content here.")


@pytest.fixture
def person_with_fields():
    return PersonEntry(
        id="doe-jane",
        title="Jane Doe",
        body="Jane is a senior engineer.",
        role="Senior Engineer",
        affiliations=["Acme Corp", "IEEE"],
        tags=["team-lead", "backend"],
    )


@pytest.fixture
def component_entry():
    """Requires software-kb plugin types — use GenericEntry with metadata."""
    from pyrite.models.generic import GenericEntry

    return GenericEntry.from_frontmatter(
        {
            "id": "kb-service",
            "title": "KB Service",
            "type": "component",
            "tags": ["core", "service"],
            "metadata": {
                "kind": "service",
                "path": "pyrite/services/kb_service.py",
                "owner": "markr",
                "dependencies": ["pyrite.config", "pyrite.storage"],
            },
        },
        body="KBService is the central orchestrator.",
    )


@pytest.fixture
def adr_entry():
    from pyrite.models.generic import GenericEntry

    return GenericEntry.from_frontmatter(
        {
            "id": "adr-0006",
            "title": "MCP Three-Tier Tool Model",
            "type": "adr",
            "tags": ["architecture", "mcp"],
            "metadata": {
                "adr_number": 6,
                "status": "accepted",
                "deciders": ["markr"],
                "date": "2025-08-01",
            },
        },
        body="## Context\n\nAI agents need different permission levels.",
    )


@pytest.fixture
def backlog_entry():
    from pyrite.models.generic import GenericEntry

    return GenericEntry.from_frontmatter(
        {
            "id": "add-export-feature",
            "title": "Add NotebookLM Export",
            "type": "backlog_item",
            "tags": ["feature", "export"],
            "metadata": {
                "kind": "feature",
                "status": "done",
                "priority": "high",
                "effort": "M",
            },
        },
        body="Export KB entries to NotebookLM format.",
    )


@pytest.fixture
def entry_with_sources():
    return NoteEntry(
        id="sourced-note",
        title="Sourced Note",
        body="Claims backed by sources.",
        sources=[
            Source(
                title="Public Report",
                url="https://example.com/report",
                outlet="Reuters",
                date="2025-01-15",
                confidence="high",
                access="public",
            ),
            Source(
                title="Confidential Tip",
                url="https://secret.example.com",
                outlet="",
                confidence="medium",
                access="restricted",
            ),
        ],
    )


@pytest.fixture
def entry_with_links():
    return PersonEntry(
        id="doe-jane",
        title="Jane Doe",
        body="Engineer at Acme.",
        role="Engineer",
        links=[
            Link(target="acme-corp", relation="employed_by"),
            Link(target="smith-john", relation="reports_to", note="Direct report"),
        ],
    )


@pytest.fixture
def entry_with_metadata():
    """Entry with extra metadata dict fields."""
    return NoteEntry(
        id="meta-note",
        title="Note With Metadata",
        body="Has extra metadata.",
        metadata={"custom_field": "custom_value", "priority": "high", "count": 42},
    )


# ---------------------------------------------------------------------------
# render_entry tests
# ---------------------------------------------------------------------------


class TestRenderEntry:
    """Test render_entry() output structure."""

    def test_simple_note_renders_title_and_body(self, simple_note):
        result = render_entry(simple_note)
        assert result.startswith("# My Note (note)")
        assert "Some content here." in result

    def test_person_renders_type_specific_fields(self, person_with_fields):
        result = render_entry(person_with_fields)
        assert "# Jane Doe (person)" in result
        assert "**role:** Senior Engineer" in result
        assert "**affiliations:** Acme Corp, IEEE" in result

    def test_component_renders_metadata_section(self, component_entry):
        result = render_entry(component_entry)
        assert "# KB Service (component)" in result
        assert "## Metadata" in result
        assert "**kind:** service" in result
        assert "**path:** pyrite/services/kb_service.py" in result
        assert "**owner:** markr" in result

    def test_adr_renders_metadata_section(self, adr_entry):
        result = render_entry(adr_entry)
        assert "# MCP Three-Tier Tool Model (adr)" in result
        assert "## Metadata" in result
        assert "**adr_number:** 6" in result
        assert "**status:** accepted" in result

    def test_backlog_renders_metadata_section(self, backlog_entry):
        result = render_entry(backlog_entry)
        assert "## Metadata" in result
        assert "**kind:** feature" in result
        assert "**status:** done" in result
        assert "**priority:** high" in result
        assert "**effort:** M" in result

    def test_tags_rendered(self, person_with_fields):
        result = render_entry(person_with_fields)
        assert "**tags:** team-lead, backend" in result

    def test_body_preserved(self, simple_note):
        result = render_entry(simple_note)
        assert "Some content here." in result

    def test_skips_internal_fields(self, simple_note):
        result = render_entry(simple_note)
        # These should not appear as rendered fields
        assert "**id:**" not in result
        assert "**_schema_version:**" not in result
        assert "**created_at:**" not in result
        assert "**updated_at:**" not in result

    def test_metadata_dict_rendered_as_section(self, entry_with_metadata):
        result = render_entry(entry_with_metadata)
        assert "## Metadata" in result
        assert "**custom_field:** custom_value" in result
        assert "**priority:** high" in result
        assert "**count:** 42" in result

    def test_empty_metadata_no_section(self, simple_note):
        result = render_entry(simple_note)
        assert "## Metadata" not in result


# ---------------------------------------------------------------------------
# Source rendering tests
# ---------------------------------------------------------------------------


class TestSourceRendering:
    """Test source rendering with different modes."""

    def test_public_mode_renders_public_sources(self, entry_with_sources):
        result = render_entry(entry_with_sources, source_mode=SourceMode.PUBLIC)
        assert "## Sources" in result
        assert "Public Report" in result
        assert "Reuters" in result
        assert "2025-01-15" in result

    def test_public_mode_skips_restricted_sources(self, entry_with_sources):
        result = render_entry(entry_with_sources, source_mode=SourceMode.PUBLIC)
        assert "Confidential Tip" not in result
        assert "secret.example.com" not in result

    def test_full_mode_renders_all_sources(self, entry_with_sources):
        result = render_entry(entry_with_sources, source_mode=SourceMode.FULL)
        assert "Public Report" in result
        assert "Confidential Tip" in result
        assert "secret.example.com" in result

    def test_redact_mode_redacts_restricted_sources(self, entry_with_sources):
        result = render_entry(entry_with_sources, source_mode=SourceMode.REDACT)
        assert "Public Report" in result
        assert "[source redacted]" in result
        assert "Confidential Tip" not in result
        assert "secret.example.com" not in result

    def test_no_sources_no_section(self, simple_note):
        result = render_entry(simple_note)
        assert "## Sources" not in result

    def test_source_confidence_shown(self, entry_with_sources):
        result = render_entry(entry_with_sources, source_mode=SourceMode.FULL)
        assert "high" in result


# ---------------------------------------------------------------------------
# Link/connection rendering tests
# ---------------------------------------------------------------------------


class TestLinkRendering:
    """Test link/connection rendering."""

    def test_links_rendered_as_connections(self, entry_with_links):
        result = render_entry(entry_with_links)
        assert "## Connections" in result
        assert "acme-corp" in result
        assert "employed_by" in result

    def test_link_note_included(self, entry_with_links):
        result = render_entry(entry_with_links)
        assert "Direct report" in result

    def test_no_links_no_section(self, simple_note):
        result = render_entry(simple_note)
        assert "## Connections" not in result


# ---------------------------------------------------------------------------
# Bundler tests
# ---------------------------------------------------------------------------


class TestBundler:
    """Test entry bundling strategies."""

    @pytest.fixture
    def many_entries(self):
        entries = []
        for i in range(10):
            entries.append(
                NoteEntry(id=f"note-{i}", title=f"Note {i}", body=f"Body {i}")
            )
        for i in range(5):
            entries.append(
                PersonEntry(
                    id=f"person-{i}", title=f"Person {i}", body=f"Bio {i}", role="Role"
                )
            )
        return entries

    def test_bundle_none_one_file_per_entry(self, many_entries):
        files = bundle_entries(many_entries, strategy=BundleStrategy.NONE)
        # One file per entry, no manifest in this dict
        assert len(files) == 15

    def test_bundle_by_type_groups(self, many_entries):
        files = bundle_entries(many_entries, strategy=BundleStrategy.BY_TYPE)
        # Two type groups: note and person
        assert len(files) == 2
        filenames = list(files.keys())
        assert any("note" in f for f in filenames)
        assert any("person" in f for f in filenames)

    def test_bundle_single_one_file(self, many_entries):
        files = bundle_entries(many_entries, strategy=BundleStrategy.SINGLE)
        assert len(files) == 1

    def test_bundle_auto_small_collection(self):
        """Under 50 entries → one-per-entry."""
        entries = [
            NoteEntry(id=f"n-{i}", title=f"Note {i}", body="x") for i in range(10)
        ]
        files = bundle_entries(entries, strategy=BundleStrategy.AUTO)
        assert len(files) == 10

    def test_bundle_auto_large_collection(self):
        """Over 50 entries → by-type."""
        entries = [
            NoteEntry(id=f"n-{i}", title=f"Note {i}", body="x") for i in range(60)
        ]
        files = bundle_entries(entries, strategy=BundleStrategy.AUTO)
        # All same type, so one file
        assert len(files) == 1

    def test_bundle_by_type_content_has_headers(self, many_entries):
        files = bundle_entries(many_entries, strategy=BundleStrategy.BY_TYPE)
        for filename, content in files.items():
            # Each entry within should still have its title as a heading
            assert "# " in content

    def test_bundle_single_content_has_all_entries(self, many_entries):
        files = bundle_entries(many_entries, strategy=BundleStrategy.SINGLE)
        content = list(files.values())[0]
        for entry in many_entries:
            assert entry.title in content


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestManifest:
    """Test manifest generation."""

    def test_manifest_has_index_table(self):
        entries = [
            NoteEntry(id="n1", title="First Note", body="x", summary="A summary"),
            PersonEntry(id="p1", title="Jane Doe", body="x", role="Engineer"),
        ]
        manifest = generate_manifest(entries, title="Test Export")
        assert "# Test Export" in manifest
        assert "First Note" in manifest
        assert "Jane Doe" in manifest
        assert "note" in manifest
        assert "person" in manifest

    def test_manifest_entry_count(self):
        entries = [
            NoteEntry(id=f"n{i}", title=f"Note {i}", body="x") for i in range(5)
        ]
        manifest = generate_manifest(entries)
        assert "5" in manifest  # entry count should appear

    def test_manifest_groups_by_type(self):
        entries = [
            NoteEntry(id="n1", title="A Note", body="x"),
            PersonEntry(id="p1", title="A Person", body="x"),
            NoteEntry(id="n2", title="Another Note", body="x"),
        ]
        manifest = generate_manifest(entries)
        # Should show type breakdown
        assert "note" in manifest.lower()
        assert "person" in manifest.lower()
