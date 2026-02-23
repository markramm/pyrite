"""Tests for the Encyclopedia extension."""

import tempfile
from pathlib import Path

from pyrite_encyclopedia.entry_types import (
    QUALITY_LEVELS,
    ArticleEntry,
    TalkPageEntry,
)
from pyrite_encyclopedia.plugin import EncyclopediaPlugin
from pyrite_encyclopedia.preset import ENCYCLOPEDIA_PRESET
from pyrite_encyclopedia.tables import ENCYCLOPEDIA_TABLES
from pyrite_encyclopedia.validators import validate_encyclopedia
from pyrite_encyclopedia.workflows import (
    ARTICLE_REVIEW_WORKFLOW,
    can_transition,
    get_allowed_transitions,
    requires_reason,
)

from pyrite.plugins.registry import PluginRegistry

# =========================================================================
# Plugin registration
# =========================================================================


class TestPluginRegistration:
    def test_plugin_has_name(self):
        plugin = EncyclopediaPlugin()
        assert plugin.name == "encyclopedia"

    def test_register_with_registry(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        assert "encyclopedia" in registry.list_plugins()

    def test_entry_types_registered(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        types = registry.get_all_entry_types()
        assert "article" in types
        assert "talk_page" in types
        assert types["article"] is ArticleEntry
        assert types["talk_page"] is TalkPageEntry

    def test_validators_registered(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        validators = registry.get_all_validators()
        assert validate_encyclopedia in validators

    def test_cli_commands_registered(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        commands = registry.get_all_cli_commands()
        cmd_names = [name for name, _ in commands]
        assert "wiki" in cmd_names

    def test_mcp_read_tools(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        tools = registry.get_all_mcp_tools("read")
        assert "wiki_quality_stats" in tools
        assert "wiki_review_queue" in tools
        assert "wiki_stubs" in tools
        assert "wiki_submit_review" not in tools
        assert "wiki_protect" not in tools

    def test_mcp_write_tools(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        tools = registry.get_all_mcp_tools("write")
        assert "wiki_quality_stats" in tools
        assert "wiki_submit_review" in tools
        assert "wiki_assess_quality" in tools
        assert "wiki_protect" not in tools  # admin only

    def test_mcp_admin_tools(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        tools = registry.get_all_mcp_tools("admin")
        assert "wiki_protect" in tools
        assert "wiki_submit_review" in tools
        assert "wiki_quality_stats" in tools

    def test_db_tables_registered(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        tables = registry.get_all_db_tables()
        table_names = [t["name"] for t in tables]
        assert "encyclopedia_review" in table_names
        assert "encyclopedia_article_history" in table_names

    def test_workflows_registered(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        workflows = registry.get_all_workflows()
        assert "article_review" in workflows
        assert workflows["article_review"]["field"] == "review_status"

    def test_kb_presets_registered(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        presets = registry.get_all_kb_presets()
        assert "encyclopedia" in presets

    def test_kb_types_registered(self):
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        kb_types = registry.get_all_kb_types()
        assert "encyclopedia" in kb_types


# =========================================================================
# Entry types
# =========================================================================


class TestArticleEntry:
    def test_default_values(self):
        entry = ArticleEntry(id="test", title="Test")
        assert entry.entry_type == "article"
        assert entry.quality == "stub"
        assert entry.review_status == "draft"
        assert entry.protection_level == "none"
        assert entry.categories == []

    def test_to_frontmatter(self):
        entry = ArticleEntry(
            id="test",
            title="General Relativity",
            quality="GA",
            review_status="published",
            protection_level="semi",
            categories=["physics", "science"],
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "article"
        assert fm["quality"] == "GA"
        assert fm["review_status"] == "published"
        assert fm["protection_level"] == "semi"
        assert fm["categories"] == ["physics", "science"]

    def test_to_frontmatter_omits_defaults(self):
        entry = ArticleEntry(id="test", title="Test")
        fm = entry.to_frontmatter()
        assert "quality" not in fm  # stub is default
        assert "review_status" not in fm  # draft is default
        assert "protection_level" not in fm  # none is default
        assert "categories" not in fm  # empty is default

    def test_from_frontmatter(self):
        meta = {
            "id": "general-relativity",
            "title": "General Relativity",
            "type": "article",
            "quality": "B",
            "review_status": "under_review",
            "protection_level": "semi",
            "categories": ["physics"],
            "tags": ["science"],
        }
        entry = ArticleEntry.from_frontmatter(meta, "Einstein's theory...")
        assert entry.id == "general-relativity"
        assert entry.quality == "B"
        assert entry.review_status == "under_review"
        assert entry.protection_level == "semi"
        assert entry.categories == ["physics"]
        assert entry.body == "Einstein's theory..."

    def test_from_frontmatter_defaults(self):
        meta = {"title": "New Article"}
        entry = ArticleEntry.from_frontmatter(meta, "")
        assert entry.quality == "stub"
        assert entry.review_status == "draft"
        assert entry.protection_level == "none"
        assert entry.categories == []

    def test_roundtrip_markdown(self):
        entry = ArticleEntry(
            id="test",
            title="Test",
            body="Article body",
            quality="GA",
            categories=["test"],
        )
        md = entry.to_markdown()
        assert "quality: GA" in md
        assert "Article body" in md


class TestTalkPageEntry:
    def test_default_values(self):
        entry = TalkPageEntry(id="test", title="Talk: Test")
        assert entry.entry_type == "talk_page"
        assert entry.article_id == ""

    def test_to_frontmatter(self):
        entry = TalkPageEntry(
            id="talk-general-relativity",
            title="Talk: General Relativity",
            article_id="general-relativity",
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "talk_page"
        assert fm["article_id"] == "general-relativity"

    def test_from_frontmatter(self):
        meta = {
            "id": "talk-test",
            "title": "Talk: Test",
            "type": "talk_page",
            "article_id": "test-article",
        }
        entry = TalkPageEntry.from_frontmatter(meta, "Discussion here")
        assert entry.article_id == "test-article"
        assert entry.body == "Discussion here"


# =========================================================================
# Validators
# =========================================================================


class TestValidators:
    def test_invalid_quality_level(self):
        errors = validate_encyclopedia("article", {"quality": "invalid"}, {})
        assert any(e["field"] == "quality" for e in errors)

    def test_valid_quality_levels(self):
        for q in QUALITY_LEVELS:
            errors = validate_encyclopedia(
                "article", {"quality": q, "body": "x" * 600, "sources": [1, 2, 3]}, {}
            )
            assert not any(e["field"] == "quality" and e["rule"] == "enum" for e in errors)

    def test_invalid_review_status(self):
        errors = validate_encyclopedia("article", {"review_status": "invalid"}, {})
        assert any(e["field"] == "review_status" for e in errors)

    def test_invalid_protection_level(self):
        errors = validate_encyclopedia("article", {"protection_level": "invalid"}, {})
        assert any(e["field"] == "protection_level" for e in errors)

    def test_ga_requires_3_sources(self):
        errors = validate_encyclopedia(
            "article",
            {"quality": "GA", "sources": [{"title": "a"}], "body": "x" * 600},
            {},
        )
        assert any(e["rule"] == "ga_min_sources" for e in errors)

    def test_ga_with_3_sources_ok(self):
        errors = validate_encyclopedia(
            "article",
            {"quality": "GA", "sources": [1, 2, 3], "body": "x" * 600},
            {},
        )
        assert not any(e["rule"] == "ga_min_sources" for e in errors)

    def test_fa_requires_3_sources(self):
        errors = validate_encyclopedia(
            "article",
            {"quality": "FA", "sources": [], "body": "x" * 600},
            {},
        )
        assert any(e["rule"] == "ga_min_sources" for e in errors)

    def test_b_requires_500_chars(self):
        errors = validate_encyclopedia(
            "article",
            {"quality": "B", "body": "short"},
            {},
        )
        assert any(e["rule"] == "b_min_length" for e in errors)

    def test_b_with_long_body_ok(self):
        errors = validate_encyclopedia(
            "article",
            {"quality": "B", "body": "x" * 500},
            {},
        )
        assert not any(e["rule"] == "b_min_length" for e in errors)

    def test_published_stub_warning(self):
        errors = validate_encyclopedia(
            "article",
            {"quality": "stub", "review_status": "published"},
            {},
        )
        warnings = [e for e in errors if e.get("severity") == "warning"]
        assert any(e["rule"] == "published_not_stub" for e in warnings)

    def test_categories_recommended_for_non_stubs(self):
        errors = validate_encyclopedia(
            "article",
            {"quality": "start"},
            {},
        )
        warnings = [e for e in errors if e.get("severity") == "warning"]
        assert any(e["rule"] == "categories_recommended" for e in warnings)

    def test_talk_page_requires_article_id(self):
        errors = validate_encyclopedia("talk_page", {}, {})
        assert any(e["field"] == "article_id" for e in errors)

    def test_talk_page_with_article_ok(self):
        errors = validate_encyclopedia("talk_page", {"article_id": "test"}, {})
        assert not any(e["field"] == "article_id" for e in errors)

    def test_ignores_other_types(self):
        errors = validate_encyclopedia("note", {}, {})
        assert errors == []


# =========================================================================
# Workflows
# =========================================================================


class TestWorkflows:
    def test_workflow_structure(self):
        wf = ARTICLE_REVIEW_WORKFLOW
        assert wf["initial"] == "draft"
        assert wf["field"] == "review_status"
        assert "draft" in wf["states"]
        assert "under_review" in wf["states"]
        assert "published" in wf["states"]

    def test_draft_to_under_review_write(self):
        assert can_transition("draft", "under_review", "write") is True

    def test_draft_to_under_review_reviewer(self):
        assert can_transition("draft", "under_review", "reviewer") is True

    def test_draft_to_published_blocked(self):
        """Can't skip review and go straight to published."""
        assert can_transition("draft", "published", "write") is False
        assert can_transition("draft", "published", "reviewer") is False

    def test_under_review_to_published_reviewer(self):
        assert can_transition("under_review", "published", "reviewer") is True

    def test_under_review_to_published_write_blocked(self):
        """Regular writers can't approve their own articles."""
        assert can_transition("under_review", "published", "write") is False

    def test_under_review_to_draft_reviewer(self):
        """Reviewers can send articles back."""
        assert can_transition("under_review", "draft", "reviewer") is True

    def test_published_to_under_review(self):
        """Published articles can be disputed."""
        assert can_transition("published", "under_review", "write") is True

    def test_published_to_under_review_requires_reason(self):
        assert requires_reason("published", "under_review") is True

    def test_draft_to_under_review_no_reason(self):
        assert requires_reason("draft", "under_review") is False

    def test_get_allowed_transitions_draft(self):
        transitions = get_allowed_transitions("draft", "write")
        targets = [t["to"] for t in transitions]
        assert "under_review" in targets
        assert "published" not in targets

    def test_get_allowed_transitions_under_review_reviewer(self):
        transitions = get_allowed_transitions("under_review", "reviewer")
        targets = [t["to"] for t in transitions]
        assert "published" in targets
        assert "draft" in targets

    def test_no_role_gets_nothing(self):
        """Without a role, no transitions are allowed."""
        transitions = get_allowed_transitions("draft", "")
        assert len(transitions) == 0

    def test_workflow_via_registry(self):
        """Test workflow validation through the registry."""
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())

        # reviewer can publish
        assert (
            registry.validate_transition("article_review", "under_review", "published", "reviewer")
            is True
        )

        # writer cannot publish
        assert (
            registry.validate_transition("article_review", "under_review", "published", "write")
            is False
        )


# =========================================================================
# Custom DB tables
# =========================================================================


class TestDBTables:
    def test_review_table_definition(self):
        review_table = next(t for t in ENCYCLOPEDIA_TABLES if t["name"] == "encyclopedia_review")
        col_names = [c["name"] for c in review_table["columns"]]
        assert "reviewer_id" in col_names
        assert "status" in col_names
        assert "comments" in col_names
        assert "entry_id" in col_names

    def test_history_table_definition(self):
        history_table = next(
            t for t in ENCYCLOPEDIA_TABLES if t["name"] == "encyclopedia_article_history"
        )
        col_names = [c["name"] for c in history_table["columns"]]
        assert "entry_id" in col_names
        assert "edit_summary" in col_names
        assert "editor_id" in col_names

    def test_tables_created_in_sqlite(self):
        """Test that the table definitions produce valid SQL."""
        import pyrite.plugins.registry as reg_module
        from pyrite.storage.database import PyriteDB

        old = reg_module._registry
        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        reg_module._registry = registry

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db = PyriteDB(Path(tmpdir) / "test.db")

                cursor = db._raw_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                table_names = [row["name"] for row in cursor.fetchall()]
                assert "encyclopedia_review" in table_names
                assert "encyclopedia_article_history" in table_names

                # Insert a review
                db._raw_conn.execute(
                    "INSERT INTO encyclopedia_review "
                    "(entry_id, kb_name, reviewer_id, status, comments, created_at) "
                    "VALUES ('a1', 'kb1', 'alice', 'approve', 'Looks good', '2025-01-01')"
                )
                db._raw_conn.commit()

                row = db._raw_conn.execute(
                    "SELECT * FROM encyclopedia_review WHERE entry_id = 'a1'"
                ).fetchone()
                assert row["reviewer_id"] == "alice"
                assert row["status"] == "approve"

                # Insert edit history
                db._raw_conn.execute(
                    "INSERT INTO encyclopedia_article_history "
                    "(entry_id, kb_name, edit_summary, editor_id, created_at) "
                    "VALUES ('a1', 'kb1', 'Added references', 'bob', '2025-01-02')"
                )
                db._raw_conn.commit()

                row = db._raw_conn.execute(
                    "SELECT * FROM encyclopedia_article_history WHERE entry_id = 'a1'"
                ).fetchone()
                assert row["editor_id"] == "bob"
                assert row["edit_summary"] == "Added references"

                db.close()
        finally:
            reg_module._registry = old


# =========================================================================
# Preset
# =========================================================================


class TestPreset:
    def test_preset_structure(self):
        p = ENCYCLOPEDIA_PRESET
        assert p["name"] == "our-encyclopedia"
        assert "article" in p["types"]
        assert "talk_page" in p["types"]
        assert p["policies"]["npov"] is True
        assert p["policies"]["require_sources"] is True
        assert p["policies"]["review_required"] is True

    def test_preset_directories(self):
        assert "articles" in ENCYCLOPEDIA_PRESET["directories"]
        assert "talk" in ENCYCLOPEDIA_PRESET["directories"]
        assert "drafts" in ENCYCLOPEDIA_PRESET["directories"]

    def test_preset_validation_rules(self):
        rules = ENCYCLOPEDIA_PRESET["validation"]["rules"]
        fields = [r["field"] for r in rules]
        assert "quality" in fields
        assert "review_status" in fields
        assert "protection_level" in fields


# =========================================================================
# Core integration
# =========================================================================


class TestCoreIntegration:
    def test_entry_class_resolution(self):
        import pyrite.plugins.registry as reg_module

        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import get_entry_class

            assert get_entry_class("article") is ArticleEntry
            assert get_entry_class("talk_page") is TalkPageEntry
        finally:
            reg_module._registry = old

    def test_entry_from_frontmatter_resolution(self):
        import pyrite.plugins.registry as reg_module

        registry = PluginRegistry()
        registry.register(EncyclopediaPlugin())
        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import entry_from_frontmatter

            entry = entry_from_frontmatter(
                {"type": "article", "title": "Test", "quality": "GA"},
                "Body",
            )
            assert isinstance(entry, ArticleEntry)
            assert entry.quality == "GA"

            entry = entry_from_frontmatter(
                {"type": "talk_page", "title": "Talk: Test", "article_id": "test"},
                "Discussion",
            )
            assert isinstance(entry, TalkPageEntry)
            assert entry.article_id == "test"
        finally:
            reg_module._registry = old

    def test_three_plugins_coexist(self):
        """All three extensions can be registered together."""
        from pyrite_social.plugin import SocialPlugin
        from pyrite_zettelkasten.plugin import ZettelkastenPlugin

        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        registry.register(SocialPlugin())
        registry.register(EncyclopediaPlugin())

        # All entry types present
        types = registry.get_all_entry_types()
        assert "zettel" in types
        assert "writeup" in types
        assert "article" in types
        assert "literature_note" in types
        assert "user_profile" in types
        assert "talk_page" in types

        # All CLI commands present
        commands = registry.get_all_cli_commands()
        cmd_names = [name for name, _ in commands]
        assert "zettel" in cmd_names
        assert "social" in cmd_names
        assert "wiki" in cmd_names

        # All presets present
        presets = registry.get_all_kb_presets()
        assert "zettelkasten" in presets
        assert "social" in presets
        assert "encyclopedia" in presets

        # All validators present (3 total from our plugins + any from entry points)
        validators = registry.get_all_validators()
        from pyrite_social.validators import validate_social
        from pyrite_zettelkasten.validators import validate_zettel

        assert validate_zettel in validators
        assert validate_social in validators
        assert validate_encyclopedia in validators

        # Workflows only from encyclopedia
        workflows = registry.get_all_workflows()
        assert "article_review" in workflows

        # DB tables from social + encyclopedia
        tables = registry.get_all_db_tables()
        table_names = [t["name"] for t in tables]
        assert "social_vote" in table_names
        assert "social_reputation_log" in table_names
        assert "encyclopedia_review" in table_names
        assert "encyclopedia_article_history" in table_names

        # Hooks only from social
        hooks = registry.get_all_hooks()
        assert "before_save" in hooks
        assert "after_save" in hooks
