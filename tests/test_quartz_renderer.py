"""Tests for Quartz renderer and site export."""

import pytest

from pyrite.models.core_types import (
    DocumentEntry,
    NoteEntry,
    PersonEntry,
)
from pyrite.models.generic import GenericEntry
from pyrite.renderers.quartz import (
    _build_frontmatter,
    _normalize_body,
    export_site,
    render_entry,
    scaffold_quartz_project,
)
from pyrite.schema import Link, Source


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_note():
    return NoteEntry(id="my-note", title="My Note", body="Some content here.")


@pytest.fixture
def person_entry():
    return PersonEntry(
        id="doe-jane",
        title="Jane Doe",
        body="Jane is a senior engineer.",
        role="Senior Engineer",
        affiliations=["Acme Corp", "IEEE"],
        tags=["team-lead", "backend"],
    )


@pytest.fixture
def entry_with_links():
    return NoteEntry(
        id="linked-note",
        title="Linked Note",
        body="See [[kb:other-entry]] and [[kb:another|Another Entry]] for details.",
        links=[
            Link(target="other-entry", relation="references"),
        ],
    )


@pytest.fixture
def entry_with_wikilinks():
    return NoteEntry(
        id="wikilink-note",
        title="Wikilink Note",
        body='Link: [[kb:target-id#heading]]\nPiped: [[ spaced | label ]]\nTransclusion: ![[embed-id]]{ view: "table", limit: 5 }',
    )


@pytest.fixture
def adr_entry():
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
def backlog_done():
    return GenericEntry.from_frontmatter(
        {
            "id": "done-item",
            "title": "Completed Feature",
            "type": "backlog_item",
            "tags": ["feature"],
            "metadata": {
                "kind": "feature",
                "status": "done",
                "priority": "low",
                "effort": "S",
            },
        },
        body="This is done.",
    )


@pytest.fixture
def mixed_entries(simple_note, person_entry, adr_entry, backlog_done):
    return [simple_note, person_entry, adr_entry, backlog_done]


# ---------------------------------------------------------------------------
# Frontmatter building
# ---------------------------------------------------------------------------


class TestBuildFrontmatter:
    def test_title_always_present(self, simple_note):
        fm = _build_frontmatter(simple_note)
        assert fm["title"] == "My Note"

    def test_id_in_aliases(self, simple_note):
        fm = _build_frontmatter(simple_note)
        assert "my-note" in fm["aliases"]

    def test_existing_aliases_preserved(self):
        entry = NoteEntry(id="test", title="Test", body="x", aliases=["alias1", "alias2"])
        fm = _build_frontmatter(entry)
        assert "test" in fm["aliases"]
        assert "alias1" in fm["aliases"]
        assert "alias2" in fm["aliases"]

    def test_tags_carried_through(self, person_entry):
        fm = _build_frontmatter(person_entry)
        assert fm["tags"] == ["team-lead", "backend"]

    def test_no_tags_when_empty(self, simple_note):
        fm = _build_frontmatter(simple_note)
        assert "tags" not in fm

    def test_summary_becomes_description(self):
        entry = NoteEntry(id="x", title="X", body="y", summary="A summary")
        fm = _build_frontmatter(entry)
        assert fm["description"] == "A summary"

    def test_no_description_without_summary(self, simple_note):
        fm = _build_frontmatter(simple_note)
        assert "description" not in fm

    def test_internal_fields_excluded(self, simple_note):
        fm = _build_frontmatter(simple_note)
        assert "id" not in fm
        assert "type" not in fm
        assert "_schema_version" not in fm
        assert "sources" not in fm
        assert "links" not in fm
        assert "provenance" not in fm


# ---------------------------------------------------------------------------
# Body normalization
# ---------------------------------------------------------------------------


class TestNormalizeBody:
    def test_kb_prefix_stripped(self):
        result = _normalize_body("See [[kb:my-entry]] for details.")
        assert result == "See [[my-entry]] for details."

    def test_kb_prefix_with_label(self):
        result = _normalize_body("See [[kb:my-entry|My Entry]] for details.")
        assert result == "See [[my-entry|My Entry]] for details."

    def test_kb_prefix_with_heading(self):
        result = _normalize_body("See [[kb:my-entry#section]].")
        assert result == "See [[my-entry#section]]."

    def test_spaced_pipes_normalized(self):
        result = _normalize_body("See [[ target | label ]] here.")
        assert result == "See [[target|label]] here."

    def test_transclusion_params_stripped(self):
        result = _normalize_body('![[my-entry]]{ view: "table", limit: 5 }')
        assert result == "![[my-entry]]"

    def test_basic_transclusion_preserved(self):
        result = _normalize_body("![[my-entry]]")
        assert result == "![[my-entry]]"

    def test_normal_wikilinks_unchanged(self):
        result = _normalize_body("See [[my-entry]] and [[other|Other]].")
        assert result == "See [[my-entry]] and [[other|Other]]."

    def test_plain_text_unchanged(self):
        result = _normalize_body("Just some plain text.")
        assert result == "Just some plain text."

    def test_multiple_normalizations(self):
        body = 'Link [[kb:a]], piped [[ b | B ]], embed ![[c]]{ view: "x" }'
        result = _normalize_body(body)
        assert "[[a]]" in result
        assert "[[b|B]]" in result
        assert "![[c]]" in result
        assert "{ view:" not in result
        assert "kb:" not in result


# ---------------------------------------------------------------------------
# render_entry
# ---------------------------------------------------------------------------


class TestRenderEntry:
    def test_has_yaml_frontmatter(self, simple_note):
        result = render_entry(simple_note)
        assert result.startswith("---\n")
        assert "\n---\n" in result

    def test_title_in_frontmatter(self, simple_note):
        result = render_entry(simple_note)
        assert "title: My Note" in result

    def test_body_after_frontmatter(self, simple_note):
        result = render_entry(simple_note)
        # Body should be after the closing ---
        parts = result.split("---")
        body_part = parts[-1]
        assert "Some content here." in body_part

    def test_aliases_include_id(self, simple_note):
        result = render_entry(simple_note)
        assert "my-note" in result

    def test_wikilinks_normalized_in_body(self, entry_with_links):
        result = render_entry(entry_with_links)
        assert "[[other-entry]]" in result
        assert "[[another|Another Entry]]" in result
        assert "kb:" not in result.split("---", 2)[-1]  # no kb: in body

    def test_tags_in_frontmatter(self, person_entry):
        result = render_entry(person_entry)
        assert "tags:" in result
        assert "team-lead" in result


# ---------------------------------------------------------------------------
# export_site
# ---------------------------------------------------------------------------


class TestExportSite:
    def test_creates_output_directory(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        result = export_site(mixed_entries, out, kb_name="Test KB")
        assert out.exists()
        assert result["entries_exported"] > 0

    def test_entries_in_type_subdirs(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        export_site(mixed_entries, out)
        # Should have type-based subdirectories
        assert (out / "note").is_dir()
        assert (out / "person").is_dir()

    def test_entry_files_created(self, tmp_path, simple_note):
        out = tmp_path / "site"
        export_site([simple_note], out)
        assert (out / "note" / "my-note.md").exists()

    def test_entry_content_is_quartz_format(self, tmp_path, simple_note):
        out = tmp_path / "site"
        export_site([simple_note], out)
        content = (out / "note" / "my-note.md").read_text()
        assert content.startswith("---\n")
        assert "title: My Note" in content
        assert "Some content here." in content

    def test_folder_index_created(self, tmp_path, simple_note):
        out = tmp_path / "site"
        export_site([simple_note], out)
        index = out / "note" / "index.md"
        assert index.exists()
        content = index.read_text()
        assert "Note" in content
        assert "[[my-note|My Note]]" in content

    def test_landing_page_created(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        export_site(mixed_entries, out, kb_name="My KB", kb_description="A test KB.")
        landing = out / "index.md"
        assert landing.exists()
        content = landing.read_text()
        assert "My KB" in content
        assert "A test KB." in content

    def test_landing_page_has_entry_count(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        result = export_site(mixed_entries, out)
        content = (out / "index.md").read_text()
        assert str(result["entries_exported"]) in content

    def test_exclude_types(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        result = export_site(mixed_entries, out, exclude_types={"backlog_item"})
        assert not (out / "backlog_item").exists()
        assert result["skipped"] >= 1

    def test_exclude_status(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        result = export_site(mixed_entries, out, exclude_statuses={"done"})
        # The backlog_done fixture has status=done in metadata
        assert result["skipped"] >= 1
        # Check the done item wasn't written
        assert not (out / "backlog_item" / "done-item.md").exists()

    def test_exclude_both(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        result = export_site(
            mixed_entries,
            out,
            exclude_types={"note"},
            exclude_statuses={"done"},
        )
        assert not (out / "note").exists()
        assert result["skipped"] >= 2

    def test_empty_entries(self, tmp_path):
        out = tmp_path / "site"
        result = export_site([], out)
        assert result["entries_exported"] == 0
        # Landing page still created
        assert (out / "index.md").exists()

    def test_files_created_count(self, tmp_path, mixed_entries):
        out = tmp_path / "site"
        result = export_site(mixed_entries, out)
        # entries + folder indexes + landing page
        assert result["files_created"] > result["entries_exported"]


# ---------------------------------------------------------------------------
# scaffold_quartz_project
# ---------------------------------------------------------------------------


class TestScaffoldQuartzProject:
    def test_creates_package_json(self, tmp_path):
        files = scaffold_quartz_project(tmp_path, kb_name="Test")
        assert "package.json" in files
        assert (tmp_path / "package.json").exists()

    def test_creates_config(self, tmp_path):
        files = scaffold_quartz_project(tmp_path, kb_name="Test")
        assert "quartz.config.ts" in files
        content = (tmp_path / "quartz.config.ts").read_text()
        assert "Test" in content

    def test_creates_layout(self, tmp_path):
        files = scaffold_quartz_project(tmp_path)
        assert "quartz.layout.ts" in files
        content = (tmp_path / "quartz.layout.ts").read_text()
        assert "Explorer" in content
        assert "Graph" in content
        assert "Backlinks" in content

    def test_creates_github_workflow(self, tmp_path):
        files = scaffold_quartz_project(tmp_path)
        assert ".github/workflows/deploy.yml" in files
        wf = (tmp_path / ".github" / "workflows" / "deploy.yml").read_text()
        assert "deploy-pages" in wf
        assert "quartz build" in wf

    def test_kb_name_in_config_title(self, tmp_path):
        scaffold_quartz_project(tmp_path, kb_name="My Investigation")
        content = (tmp_path / "quartz.config.ts").read_text()
        assert "My Investigation" in content

    def test_idempotent(self, tmp_path):
        scaffold_quartz_project(tmp_path, kb_name="First")
        scaffold_quartz_project(tmp_path, kb_name="Second")
        content = (tmp_path / "quartz.config.ts").read_text()
        assert "Second" in content
