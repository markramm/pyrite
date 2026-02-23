"""Tests for the Template Service."""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.template_service import TemplateService


@pytest.fixture
def kb_dir():
    """Create a temporary KB directory with sample templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir) / "test-kb"
        kb_path.mkdir()
        tpl_dir = kb_path / "_templates"
        tpl_dir.mkdir()

        # meeting-note template
        (tpl_dir / "meeting-note.md").write_text(
            "---\n"
            'template_name: "Meeting Note"\n'
            'template_description: "Template for meeting notes"\n'
            "entry_type: meeting\n"
            "tags: [meeting]\n"
            "---\n"
            "## Attendees\n"
            "- {{attendees}}\n"
            "\n"
            "## Date: {{date}}\n"
            "\n"
            "## Notes\n"
            "{{notes}}\n"
        )

        # research-brief template
        (tpl_dir / "research-brief.md").write_text(
            "---\n"
            'template_name: "Research Brief"\n'
            'template_description: "Quick research summary"\n'
            "entry_type: note\n"
            "tags: [research]\n"
            "---\n"
            "# {{title}}\n"
            "\n"
            "**KB:** {{kb}}\n"
            "**Author:** {{author}}\n"
            "**Date:** {{date}}\n"
            "\n"
            "## Summary\n"
        )

        yield kb_path


@pytest.fixture
def empty_kb_dir():
    """Create a KB directory with no _templates folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir) / "empty-kb"
        kb_path.mkdir()
        yield kb_path


@pytest.fixture
def config(kb_dir):
    """PyriteConfig with a single test KB."""
    return PyriteConfig(
        knowledge_bases=[
            KBConfig(name="test-kb", path=kb_dir, kb_type="generic"),
        ],
        settings=Settings(),
    )


@pytest.fixture
def config_empty(empty_kb_dir):
    """PyriteConfig with an empty KB (no _templates dir)."""
    return PyriteConfig(
        knowledge_bases=[
            KBConfig(name="empty-kb", path=empty_kb_dir, kb_type="generic"),
        ],
        settings=Settings(),
    )


@pytest.fixture
def svc(config):
    return TemplateService(config)


@pytest.fixture
def svc_empty(config_empty):
    return TemplateService(config_empty)


# ---- Listing tests ----


class TestListTemplates:
    def test_lists_templates_with_names_and_descriptions(self, svc):
        templates = svc.list_templates("test-kb")
        assert len(templates) == 2
        names = {t["name"] for t in templates}
        assert "Meeting Note" in names
        assert "Research Brief" in names

    def test_includes_entry_type(self, svc):
        templates = svc.list_templates("test-kb")
        by_name = {t["name"]: t for t in templates}
        assert by_name["Meeting Note"]["entry_type"] == "meeting"
        assert by_name["Research Brief"]["entry_type"] == "note"

    def test_empty_template_directory(self, svc_empty):
        templates = svc_empty.list_templates("empty-kb")
        assert templates == []

    def test_missing_kb_raises(self, svc):
        with pytest.raises(KeyError, match="not found"):
            svc.list_templates("nonexistent-kb")


# ---- Get template tests ----


class TestGetTemplate:
    def test_get_existing_template(self, svc):
        tpl = svc.get_template("test-kb", "meeting-note")
        assert tpl["name"] == "Meeting Note"
        assert tpl["description"] == "Template for meeting notes"
        assert tpl["entry_type"] == "meeting"
        assert "{{attendees}}" in tpl["body"]
        assert "tags" in tpl["frontmatter"]
        assert tpl["frontmatter"]["tags"] == ["meeting"]

    def test_frontmatter_excludes_template_meta_fields(self, svc):
        tpl = svc.get_template("test-kb", "meeting-note")
        assert "template_name" not in tpl["frontmatter"]
        assert "template_description" not in tpl["frontmatter"]

    def test_missing_template_raises(self, svc):
        with pytest.raises(FileNotFoundError, match="not found"):
            svc.get_template("test-kb", "nonexistent")

    def test_missing_kb_raises(self, svc):
        with pytest.raises(KeyError, match="not found"):
            svc.get_template("no-kb", "meeting-note")


# ---- Render tests ----


class TestRenderTemplate:
    def test_renders_builtin_date_variable(self, svc):
        result = svc.render_template("test-kb", "meeting-note", {})
        # Should contain today's date in YYYY-MM-DD format, not {{date}}
        assert "{{date}}" not in result["body"]
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2}", result["body"])

    def test_renders_title_and_kb_variables(self, svc):
        result = svc.render_template(
            "test-kb",
            "research-brief",
            {"title": "My Research", "author": "Jane"},
        )
        assert "# My Research" in result["body"]
        assert "**KB:** test-kb" in result["body"]
        assert "**Author:** Jane" in result["body"]

    def test_leaves_custom_placeholders_intact(self, svc):
        result = svc.render_template("test-kb", "meeting-note", {})
        # {{attendees}} and {{notes}} are custom — should remain
        assert "{{attendees}}" in result["body"]
        assert "{{notes}}" in result["body"]

    def test_custom_variable_gets_replaced(self, svc):
        result = svc.render_template(
            "test-kb",
            "meeting-note",
            {"attendees": "Alice, Bob"},
        )
        assert "Alice, Bob" in result["body"]
        assert "{{attendees}}" not in result["body"]

    def test_returns_entry_type(self, svc):
        result = svc.render_template("test-kb", "meeting-note", {})
        assert result["entry_type"] == "meeting"

    def test_returns_frontmatter(self, svc):
        result = svc.render_template("test-kb", "meeting-note", {})
        assert result["frontmatter"]["tags"] == ["meeting"]

    def test_missing_template_raises(self, svc):
        with pytest.raises(FileNotFoundError):
            svc.render_template("test-kb", "nonexistent", {})

    def test_missing_kb_raises(self, svc):
        with pytest.raises(KeyError):
            svc.render_template("no-kb", "meeting-note", {})
