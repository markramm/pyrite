"""
Tests for Git-Backed Personal KBs and Usage Tiers.

Covers:
- UsageTierConfig defaults and parsing
- Usage tier enforcement (KB creation limits, entry count limits)
- KB export to directory (markdown files with frontmatter)
- Migration v10 (usage_tier column on local_user)
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings, UsageTierConfig
from pyrite.exceptions import PyriteError
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from pyrite.storage.migrations import CURRENT_VERSION, MigrationManager


# =========================================================================
# Config Tests
# =========================================================================


class TestUsageTierConfig:
    """Tests for UsageTierConfig dataclass."""

    def test_usage_tier_config_defaults(self):
        """Default tier has expected limits."""
        tier = UsageTierConfig()
        assert tier.max_personal_kbs == 1
        assert tier.max_entries_per_kb == 500
        assert tier.max_storage_mb == 50
        assert tier.allow_private_repos is False
        assert tier.rate_limit_read == "100/minute"
        assert tier.rate_limit_write == "30/minute"

    def test_usage_tier_config_from_yaml(self):
        """Tiers parsed from config dict via AuthConfig."""
        auth = AuthConfig(
            usage_tiers={
                "free": UsageTierConfig(max_personal_kbs=1, max_entries_per_kb=100),
                "pro": UsageTierConfig(
                    max_personal_kbs=10,
                    max_entries_per_kb=5000,
                    max_storage_mb=500,
                    allow_private_repos=True,
                ),
            }
        )
        assert "free" in auth.usage_tiers
        assert "pro" in auth.usage_tiers
        assert auth.usage_tiers["free"].max_personal_kbs == 1
        assert auth.usage_tiers["free"].max_entries_per_kb == 100
        assert auth.usage_tiers["pro"].max_personal_kbs == 10
        assert auth.usage_tiers["pro"].allow_private_repos is True

    def test_no_tiers_configured(self):
        """No tiers = no limits enforced (empty dict default)."""
        auth = AuthConfig()
        assert auth.usage_tiers == {}


# =========================================================================
# Usage Tier Enforcement Tests
# =========================================================================


class TestUsageTierEnforcement:
    """Tests for usage tier limit checking."""

    @pytest.fixture()
    def kb_service(self, tmp_path):
        """Create a KBService with a real DB for tier testing."""
        db_path = tmp_path / "test.db"
        db = PyriteDB(str(db_path))

        kb_dir = tmp_path / "test-kb"
        kb_dir.mkdir()

        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="test-kb", path=kb_dir, kb_type="generic"),
            ],
            settings=Settings(
                index_path=db_path,
                auth=AuthConfig(
                    usage_tiers={
                        "default": UsageTierConfig(
                            max_personal_kbs=2,
                            max_entries_per_kb=3,
                        ),
                    }
                ),
            ),
        )

        svc = KBService(config, db)
        return svc

    def test_kb_creation_within_limits(self, kb_service):
        """Creating KB when under limit succeeds."""
        # User has 0 KBs, limit is 2 — should succeed
        allowed, msg = kb_service.check_kb_creation_allowed(
            user_id=1, user_tier="default", current_kb_count=0
        )
        assert allowed is True

    def test_kb_creation_exceeds_limit(self, kb_service):
        """Creating KB when at limit raises error."""
        # User already has 2 KBs, limit is 2 — should fail
        allowed, msg = kb_service.check_kb_creation_allowed(
            user_id=1, user_tier="default", current_kb_count=2
        )
        assert allowed is False
        assert "limit" in msg.lower()

    def test_entry_count_limit_enforced(self, kb_service):
        """Adding entry past limit raises error."""
        # KB already has 3 entries, limit is 3 — should fail
        allowed, msg = kb_service.check_entry_creation_allowed(
            kb_name="test-kb", user_tier="default", current_entry_count=3
        )
        assert allowed is False
        assert "limit" in msg.lower()

    def test_no_limits_when_unconfigured(self, tmp_path):
        """No usage_tiers config = unlimited."""
        db_path = tmp_path / "test.db"
        db = PyriteDB(str(db_path))

        config = PyriteConfig(
            settings=Settings(
                index_path=db_path,
                auth=AuthConfig(),  # No usage_tiers
            ),
        )

        svc = KBService(config, db)
        # No tiers configured — should always allow
        allowed, msg = svc.check_kb_creation_allowed(
            user_id=1, user_tier="default", current_kb_count=999
        )
        assert allowed is True

        allowed, msg = svc.check_entry_creation_allowed(
            kb_name="any", user_tier="default", current_entry_count=999999
        )
        assert allowed is True


# =========================================================================
# Export Flow Tests
# =========================================================================


class TestKBExport:
    """Tests for KB export to directory."""

    @pytest.fixture()
    def kb_with_entries(self, tmp_path):
        """Create a KBService with a KB containing entries."""
        db_path = tmp_path / "test.db"
        db = PyriteDB(str(db_path))

        kb_dir = tmp_path / "myproject"
        kb_dir.mkdir()

        # Create a kb.yaml in the KB directory
        kb_yaml = kb_dir / "kb.yaml"
        kb_yaml.write_text("name: myproject\ntype: generic\ndescription: Test KB\n")

        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="myproject", path=kb_dir, kb_type="generic"),
            ],
            settings=Settings(index_path=db_path),
        )

        svc = KBService(config, db)

        # Create a few entries using the service
        svc.create_entry(
            kb_name="myproject",
            entry_id="design-doc-auth",
            title="Auth Design Document",
            entry_type="note",
            body="## Overview\nAuthentication uses OAuth2.",
            tags=["design", "auth"],
        )
        svc.create_entry(
            kb_name="myproject",
            entry_id="api-spec",
            title="API Specification",
            entry_type="note",
            body="REST API follows OpenAPI 3.0.",
            tags=["api"],
        )

        return svc, tmp_path

    def test_export_kb_creates_markdown_files(self, kb_with_entries):
        """Entries exported as markdown with frontmatter."""
        svc, tmp_path = kb_with_entries
        export_dir = tmp_path / "export"
        export_dir.mkdir()

        result = svc.export_kb_to_directory("myproject", export_dir)

        assert result["entries_exported"] >= 2
        assert result["files_created"] >= 2

        # Check that markdown files were created
        md_files = list(export_dir.rglob("*.md"))
        assert len(md_files) >= 2

        # Check frontmatter is present in at least one file
        content = None
        for f in md_files:
            text = f.read_text()
            if "Auth Design Document" in text:
                content = text
                break

        assert content is not None
        assert content.startswith("---")
        assert "title:" in content
        assert "Auth Design Document" in content

    def test_export_kb_includes_kb_yaml(self, kb_with_entries):
        """kb.yaml included in export."""
        svc, tmp_path = kb_with_entries
        export_dir = tmp_path / "export"
        export_dir.mkdir()

        svc.export_kb_to_directory("myproject", export_dir)

        kb_yaml = export_dir / "kb.yaml"
        assert kb_yaml.exists()
        content = kb_yaml.read_text()
        assert "myproject" in content

    def test_export_kb_empty_kb(self, tmp_path):
        """Empty KB export succeeds with just kb.yaml."""
        db_path = tmp_path / "test.db"
        db = PyriteDB(str(db_path))

        kb_dir = tmp_path / "empty-kb"
        kb_dir.mkdir()

        # Create a kb.yaml
        kb_yaml = kb_dir / "kb.yaml"
        kb_yaml.write_text("name: empty-kb\ntype: generic\n")

        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="empty-kb", path=kb_dir, kb_type="generic"),
            ],
            settings=Settings(index_path=db_path),
        )

        svc = KBService(config, db)
        export_dir = tmp_path / "export"
        export_dir.mkdir()

        result = svc.export_kb_to_directory("empty-kb", export_dir)

        assert result["entries_exported"] == 0
        assert result["files_created"] == 0
        # kb.yaml should still be copied
        assert (export_dir / "kb.yaml").exists()


# =========================================================================
# Migration Test
# =========================================================================


class TestMigrationV10:
    """Test that v10 migration adds usage_tier column to local_user."""

    def test_migration_adds_usage_tier_column(self, tmp_path):
        """v10 migration adds usage_tier column to local_user."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create the local_user table as it would exist after v6
        conn.execute("""
            CREATE TABLE IF NOT EXISTS local_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'read',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        """)
        conn.commit()

        mgr = MigrationManager(conn)

        # Record that we've applied v1-v9 so only v10 runs
        from datetime import UTC, datetime

        for v in range(1, 10):
            conn.execute(
                "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
                (v, f"Migration v{v}", datetime.now(UTC).isoformat()),
            )
        conn.commit()

        # Apply pending migrations (should include v10)
        applied = mgr.migrate()
        assert any(m.version == 10 for m in applied)

        # Check that usage_tier column exists
        columns = {row[1] for row in conn.execute("PRAGMA table_info(local_user)").fetchall()}
        assert "usage_tier" in columns

        # Check default value
        conn.execute(
            "INSERT INTO local_user (username, password_hash) VALUES ('testuser', 'hash123')"
        )
        row = conn.execute("SELECT usage_tier FROM local_user WHERE username = 'testuser'").fetchone()
        assert row[0] == "default"

        conn.close()

    def test_current_version_is_10(self):
        """CURRENT_VERSION is 10 after migration."""
        assert CURRENT_VERSION == 10
