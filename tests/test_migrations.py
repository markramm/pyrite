"""Tests for schema migration system."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from pyrite.storage.migrations import (
    CURRENT_VERSION,
    MIGRATIONS,
    MigrationManager,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
    db_path.unlink()


class TestMigrationManager:
    """Tests for MigrationManager."""

    def test_creates_version_table(self, temp_db):
        """Migration manager creates schema_version table."""
        mgr = MigrationManager(temp_db)

        # Check table exists
        row = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        assert row is not None

    def test_initial_version_is_zero(self, temp_db):
        """Fresh database has version 0."""
        mgr = MigrationManager(temp_db)
        assert mgr.get_current_version() == 0

    def test_migrate_applies_migrations(self, temp_db):
        """migrate() applies pending migrations."""
        mgr = MigrationManager(temp_db)

        applied = mgr.migrate()

        assert len(applied) == len(MIGRATIONS)
        assert mgr.get_current_version() == CURRENT_VERSION

    def test_migrate_is_idempotent(self, temp_db):
        """Running migrate() twice doesn't re-apply migrations."""
        mgr = MigrationManager(temp_db)

        applied1 = mgr.migrate()
        applied2 = mgr.migrate()

        assert len(applied1) > 0
        assert len(applied2) == 0

    def test_get_pending_migrations(self, temp_db):
        """get_pending_migrations returns unapplied migrations."""
        mgr = MigrationManager(temp_db)

        pending = mgr.get_pending_migrations()
        assert len(pending) == len(MIGRATIONS)

        mgr.migrate()
        pending = mgr.get_pending_migrations()
        assert len(pending) == 0

    def test_get_applied_migrations(self, temp_db):
        """get_applied_migrations returns applied migration records."""
        mgr = MigrationManager(temp_db)

        applied = mgr.get_applied_migrations()
        assert len(applied) == 0

        mgr.migrate()
        applied = mgr.get_applied_migrations()
        assert len(applied) == len(MIGRATIONS)
        assert all("version" in m and "applied_at" in m for m in applied)

    def test_status_returns_summary(self, temp_db):
        """status() returns migration summary."""
        mgr = MigrationManager(temp_db)

        status = mgr.status()
        assert status["current_version"] == 0
        assert status["target_version"] == CURRENT_VERSION
        assert status["up_to_date"] is False
        assert len(status["pending"]) > 0

        mgr.migrate()
        status = mgr.status()
        assert status["current_version"] == CURRENT_VERSION
        assert status["up_to_date"] is True
        assert len(status["pending"]) == 0

    def test_migrate_to_specific_version(self, temp_db):
        """migrate() can target a specific version."""
        mgr = MigrationManager(temp_db)

        # Only migrate to version 1 (even if more exist in future)
        mgr.migrate(target_version=1)

        assert mgr.get_current_version() == 1


class TestMigrationStructure:
    """Tests for migration definitions."""

    def test_migrations_have_required_fields(self):
        """All migrations have required fields."""
        for m in MIGRATIONS:
            assert isinstance(m.version, int)
            assert m.version > 0
            assert isinstance(m.description, str)
            assert len(m.description) > 0
            assert isinstance(m.up, str)
            assert isinstance(m.down, str)

    def test_migrations_are_sequential(self):
        """Migrations have sequential version numbers."""
        versions = [m.version for m in MIGRATIONS]
        expected = list(range(1, len(MIGRATIONS) + 1))
        assert versions == expected

    def test_current_version_matches_latest_migration(self):
        """CURRENT_VERSION matches the latest migration."""
        if MIGRATIONS:
            assert CURRENT_VERSION == MIGRATIONS[-1].version

    def test_migration_v2_exists(self):
        """Migration v2 for vector search exists."""
        v2 = [m for m in MIGRATIONS if m.version == 2]
        assert len(v2) == 1
        assert "vec" in v2[0].description.lower()

    def test_migration_v2_has_rollback(self):
        """Migration v2 has rollback SQL."""
        v2 = [m for m in MIGRATIONS if m.version == 2][0]
        assert "DROP TABLE" in v2.down
