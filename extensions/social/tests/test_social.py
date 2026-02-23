"""Tests for the Social KB extension."""

import sqlite3
from pathlib import Path

import pytest
from pyrite_social.entry_types import WRITEUP_TYPES, UserProfileEntry, WriteupEntry
from pyrite_social.hooks import before_save_author_check
from pyrite_social.plugin import SocialPlugin
from pyrite_social.preset import SOCIAL_PRESET
from pyrite_social.tables import SOCIAL_TABLES
from pyrite_social.validators import validate_social

from pyrite.plugins.registry import PluginRegistry

# =========================================================================
# Plugin registration
# =========================================================================


class TestPluginRegistration:
    def test_plugin_has_name(self):
        plugin = SocialPlugin()
        assert plugin.name == "social"

    def test_register_with_registry(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        assert "social" in registry.list_plugins()

    def test_entry_types_registered(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        types = registry.get_all_entry_types()
        assert "writeup" in types
        assert "user_profile" in types
        assert types["writeup"] is WriteupEntry
        assert types["user_profile"] is UserProfileEntry

    def test_validators_registered(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        validators = registry.get_all_validators()
        assert validate_social in validators

    def test_cli_commands_registered(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        commands = registry.get_all_cli_commands()
        cmd_names = [name for name, _ in commands]
        assert "social" in cmd_names

    def test_mcp_read_tools(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        tools = registry.get_all_mcp_tools("read")
        assert "social_top" in tools
        assert "social_newest" in tools
        assert "social_reputation" in tools
        assert "social_vote" not in tools  # write-only
        assert "social_post" not in tools  # write-only

    def test_mcp_write_tools(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        tools = registry.get_all_mcp_tools("write")
        assert "social_top" in tools
        assert "social_vote" in tools
        assert "social_post" in tools

    def test_db_tables_registered(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        tables = registry.get_all_db_tables()
        table_names = [t["name"] for t in tables]
        assert "social_vote" in table_names
        assert "social_reputation_log" in table_names

    def test_hooks_registered(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        hooks = registry.get_all_hooks()
        assert "before_save" in hooks
        assert "after_save" in hooks
        assert "after_delete" in hooks
        assert before_save_author_check in hooks["before_save"]

    def test_kb_presets_registered(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        presets = registry.get_all_kb_presets()
        assert "social" in presets

    def test_kb_types_registered(self):
        registry = PluginRegistry()
        registry.register(SocialPlugin())
        kb_types = registry.get_all_kb_types()
        assert "social" in kb_types


# =========================================================================
# Entry types
# =========================================================================


class TestWriteupEntry:
    def test_default_values(self):
        entry = WriteupEntry(id="test", title="Test")
        assert entry.entry_type == "writeup"
        assert entry.author_id == ""
        assert entry.writeup_type == "essay"
        assert entry.allow_voting is True

    def test_to_frontmatter(self):
        entry = WriteupEntry(
            id="test",
            title="My Essay",
            author_id="alice",
            writeup_type="opinion",
            allow_voting=False,
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "writeup"
        assert fm["author_id"] == "alice"
        assert fm["writeup_type"] == "opinion"
        assert fm["allow_voting"] is False

    def test_to_frontmatter_omits_defaults(self):
        entry = WriteupEntry(id="test", title="Test", author_id="bob")
        fm = entry.to_frontmatter()
        assert "writeup_type" not in fm  # essay is default
        assert "allow_voting" not in fm  # True is default
        assert fm["author_id"] == "bob"

    def test_from_frontmatter(self):
        meta = {
            "id": "my-essay",
            "title": "My Essay",
            "type": "writeup",
            "author_id": "alice",
            "writeup_type": "review",
            "allow_voting": False,
            "tags": ["review"],
        }
        entry = WriteupEntry.from_frontmatter(meta, "Great review")
        assert entry.id == "my-essay"
        assert entry.title == "My Essay"
        assert entry.author_id == "alice"
        assert entry.writeup_type == "review"
        assert entry.allow_voting is False
        assert entry.body == "Great review"
        assert entry.tags == ["review"]

    def test_from_frontmatter_defaults(self):
        meta = {"title": "Quick Post"}
        entry = WriteupEntry.from_frontmatter(meta, "")
        assert entry.author_id == ""
        assert entry.writeup_type == "essay"
        assert entry.allow_voting is True


class TestUserProfileEntry:
    def test_default_values(self):
        entry = UserProfileEntry(id="alice", title="Alice")
        assert entry.entry_type == "user_profile"
        assert entry.reputation == 0
        assert entry.join_date == ""
        assert entry.writeup_count == 0

    def test_to_frontmatter(self):
        entry = UserProfileEntry(
            id="alice",
            title="Alice",
            reputation=42,
            join_date="2025-01-01",
            writeup_count=10,
        )
        fm = entry.to_frontmatter()
        assert fm["type"] == "user_profile"
        assert fm["reputation"] == 42
        assert fm["join_date"] == "2025-01-01"
        assert fm["writeup_count"] == 10

    def test_from_frontmatter(self):
        meta = {
            "id": "alice",
            "title": "Alice",
            "type": "user_profile",
            "reputation": 42,
            "join_date": "2025-01-01",
            "writeup_count": 10,
        }
        entry = UserProfileEntry.from_frontmatter(meta, "Alice's bio")
        assert entry.reputation == 42
        assert entry.join_date == "2025-01-01"
        assert entry.writeup_count == 10
        assert entry.body == "Alice's bio"


# =========================================================================
# Validators
# =========================================================================


class TestValidators:
    def test_writeup_requires_author_id(self):
        errors = validate_social("writeup", {}, {})
        assert any(e["field"] == "author_id" for e in errors)

    def test_writeup_with_author_ok(self):
        errors = validate_social("writeup", {"author_id": "alice"}, {})
        assert not any(e["field"] == "author_id" for e in errors)

    def test_writeup_invalid_type(self):
        errors = validate_social("writeup", {"author_id": "alice", "writeup_type": "invalid"}, {})
        assert any(e["field"] == "writeup_type" for e in errors)

    def test_writeup_valid_types(self):
        for wt in WRITEUP_TYPES:
            errors = validate_social("writeup", {"author_id": "alice", "writeup_type": wt}, {})
            assert not any(e["field"] == "writeup_type" for e in errors)

    def test_ignores_other_types(self):
        errors = validate_social("note", {"title": "regular note"}, {})
        assert errors == []


# =========================================================================
# Hooks
# =========================================================================


class TestHooks:
    def test_before_save_sets_author_on_create(self):
        entry = WriteupEntry(id="test", title="Test")
        ctx = {"user": "alice", "operation": "create"}
        result = before_save_author_check(entry, ctx)
        assert result.author_id == "alice"

    def test_before_save_preserves_existing_author(self):
        entry = WriteupEntry(id="test", title="Test", author_id="bob")
        ctx = {"user": "alice", "operation": "create"}
        result = before_save_author_check(entry, ctx)
        assert result.author_id == "bob"  # bob was already set

    def test_before_save_allows_author_update(self):
        entry = WriteupEntry(id="test", title="Test", author_id="alice")
        ctx = {"user": "alice", "operation": "update"}
        result = before_save_author_check(entry, ctx)
        assert result.author_id == "alice"

    def test_before_save_blocks_non_author_update(self):
        entry = WriteupEntry(id="test", title="Test", author_id="alice")
        ctx = {"user": "bob", "operation": "update"}
        with pytest.raises(PermissionError, match="bob.*cannot edit.*alice"):
            before_save_author_check(entry, ctx)

    def test_before_save_ignores_non_writeups(self):
        from pyrite.models.core_types import NoteEntry

        entry = NoteEntry(id="test", title="Test")
        ctx = {"user": "alice", "operation": "create"}
        result = before_save_author_check(entry, ctx)
        assert result is entry  # unchanged

    def test_before_save_allows_update_without_user(self):
        """If no user in context, skip the check (e.g., system operations)."""
        entry = WriteupEntry(id="test", title="Test", author_id="alice")
        ctx = {"user": "", "operation": "update"}
        result = before_save_author_check(entry, ctx)
        assert result is entry

    def test_hooks_run_via_registry(self):
        """Test that hooks fire through the registry's run_hooks method."""
        registry = PluginRegistry()
        registry.register(SocialPlugin())

        entry = WriteupEntry(id="test", title="Test")
        ctx = {"user": "alice", "operation": "create"}
        result = registry.run_hooks("before_save", entry, ctx)
        assert result.author_id == "alice"

    def test_hooks_abort_on_permission_error(self):
        """Test that before_save hooks can abort via the registry."""
        registry = PluginRegistry()
        registry.register(SocialPlugin())

        entry = WriteupEntry(id="test", title="Test", author_id="alice")
        ctx = {"user": "bob", "operation": "update"}
        with pytest.raises(PermissionError):
            registry.run_hooks("before_save", entry, ctx)


# =========================================================================
# Custom DB tables
# =========================================================================


class TestDBTables:
    def test_vote_table_definition(self):
        vote_table = next(t for t in SOCIAL_TABLES if t["name"] == "social_vote")
        col_names = [c["name"] for c in vote_table["columns"]]
        assert "id" in col_names
        assert "entry_id" in col_names
        assert "kb_name" in col_names
        assert "user_id" in col_names
        assert "value" in col_names
        assert "created_at" in col_names

    def test_vote_table_has_unique_constraint(self):
        vote_table = next(t for t in SOCIAL_TABLES if t["name"] == "social_vote")
        unique_indexes = [i for i in vote_table["indexes"] if i.get("unique")]
        assert len(unique_indexes) == 1
        assert set(unique_indexes[0]["columns"]) == {"entry_id", "kb_name", "user_id"}

    def test_reputation_log_table_definition(self):
        rep_table = next(t for t in SOCIAL_TABLES if t["name"] == "social_reputation_log")
        col_names = [c["name"] for c in rep_table["columns"]]
        assert "user_id" in col_names
        assert "delta" in col_names
        assert "reason" in col_names

    def test_tables_created_in_sqlite(self):
        """Test that the table definitions produce valid SQL."""
        import tempfile

        from pyrite.storage.database import PyriteDB

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Manually register plugin before creating DB
            import pyrite.plugins.registry as reg_module

            old = reg_module._registry
            registry = PluginRegistry()
            registry.register(SocialPlugin())
            reg_module._registry = registry

            try:
                db = PyriteDB(db_path)

                # Verify tables exist
                cursor = db._raw_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                table_names = [row["name"] for row in cursor.fetchall()]
                assert "social_vote" in table_names
                assert "social_reputation_log" in table_names

                # Verify we can insert and query
                db._raw_conn.execute(
                    "INSERT INTO social_vote (entry_id, kb_name, user_id, value, created_at) "
                    "VALUES ('e1', 'kb1', 'alice', 1, '2025-01-01')"
                )
                db._raw_conn.commit()

                row = db._raw_conn.execute(
                    "SELECT * FROM social_vote WHERE entry_id = 'e1'"
                ).fetchone()
                assert row["user_id"] == "alice"
                assert row["value"] == 1

                # Verify unique constraint
                with pytest.raises(sqlite3.IntegrityError):
                    db._raw_conn.execute(
                        "INSERT INTO social_vote (entry_id, kb_name, user_id, value, created_at) "
                        "VALUES ('e1', 'kb1', 'alice', -1, '2025-01-02')"
                    )

                db.close()
            finally:
                reg_module._registry = old


# =========================================================================
# Preset
# =========================================================================


class TestPreset:
    def test_preset_structure(self):
        p = SOCIAL_PRESET
        assert p["name"] == "my-community"
        assert "writeup" in p["types"]
        assert "user_profile" in p["types"]
        assert p["policies"]["public"] is True
        assert p["policies"]["author_edit_only"] is True
        assert p["policies"]["voting_enabled"] is True

    def test_preset_directories(self):
        assert "writeups" in SOCIAL_PRESET["directories"]
        assert "users" in SOCIAL_PRESET["directories"]


# =========================================================================
# Core integration
# =========================================================================


class TestCoreIntegration:
    def test_entry_class_resolution(self):
        import pyrite.plugins.registry as reg_module

        registry = PluginRegistry()
        registry.register(SocialPlugin())
        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import get_entry_class

            assert get_entry_class("writeup") is WriteupEntry
            assert get_entry_class("user_profile") is UserProfileEntry
        finally:
            reg_module._registry = old

    def test_entry_from_frontmatter_resolution(self):
        import pyrite.plugins.registry as reg_module

        registry = PluginRegistry()
        registry.register(SocialPlugin())
        old = reg_module._registry
        reg_module._registry = registry

        try:
            from pyrite.models.core_types import entry_from_frontmatter

            entry = entry_from_frontmatter(
                {"type": "writeup", "title": "Test", "author_id": "alice"},
                "Body",
            )
            assert isinstance(entry, WriteupEntry)
            assert entry.author_id == "alice"
        finally:
            reg_module._registry = old

    def test_multiple_plugins_coexist(self):
        """Both zettelkasten and social plugins can be registered together."""
        from pyrite_zettelkasten.entry_types import ZettelEntry
        from pyrite_zettelkasten.plugin import ZettelkastenPlugin

        registry = PluginRegistry()
        registry.register(ZettelkastenPlugin())
        registry.register(SocialPlugin())

        types = registry.get_all_entry_types()
        assert "zettel" in types
        assert "writeup" in types
        assert types["zettel"] is ZettelEntry
        assert types["writeup"] is WriteupEntry

        # Both provide validators
        validators = registry.get_all_validators()
        assert len(validators) >= 2

        # Both provide CLI commands
        commands = registry.get_all_cli_commands()
        cmd_names = [name for name, _ in commands]
        assert "zettel" in cmd_names
        assert "social" in cmd_names

        # Both provide presets
        presets = registry.get_all_kb_presets()
        assert "zettelkasten" in presets
        assert "social" in presets
