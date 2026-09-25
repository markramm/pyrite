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


class TestEntryVersionFilePathMigration:
    """v25 adds entry_version.file_path so a stored version can be read at
    the path it had at commit time, not just the entry's current path
    (#432): an existing DB's entry_version rows survive the upgrade, and a
    fresh column is added to old (pre-#432) rows without one."""

    def test_v25_adds_file_path_column(self, temp_db):
        # Build the schema as it existed before v25: run migrations up to
        # v24, then create entry_version by hand the way v2's SQL did (no
        # file_path column), simulating an existing database.
        mgr = MigrationManager(temp_db)
        mgr.migrate(target_version=24)
        cols_before = {row[1] for row in temp_db.execute("PRAGMA table_info(entry_version)")}
        assert "file_path" not in cols_before

        mgr.migrate()

        assert mgr.get_current_version() == CURRENT_VERSION
        cols_after = {row[1] for row in temp_db.execute("PRAGMA table_info(entry_version)")}
        assert "file_path" in cols_after

    def test_v25_preserves_existing_rows(self, temp_db):
        mgr = MigrationManager(temp_db)
        mgr.migrate(target_version=24)
        temp_db.execute("""
            INSERT INTO entry_version
                (entry_id, kb_name, commit_hash, author_name, author_email,
                 commit_date, message, change_type)
            VALUES ('e1', 'kb1', 'deadbeef', 'A', 'a@x.com', '2026-01-01', 'msg', 'modified')
        """)
        temp_db.commit()

        mgr.migrate()

        row = temp_db.execute(
            "SELECT entry_id, commit_hash, file_path FROM entry_version WHERE entry_id = 'e1'"
        ).fetchone()
        assert row is not None
        assert row["commit_hash"] == "deadbeef"
        assert row["file_path"] is None

    def test_v25_is_idempotent(self, temp_db):
        mgr = MigrationManager(temp_db)
        mgr.migrate(target_version=24)
        mgr.migrate()
        # Re-running (e.g. a second migrate() call, or applying on a DB that
        # already had the column from ORM create_all) must not error.
        mgr.migrate()
        cols = {row[1] for row in temp_db.execute("PRAGMA table_info(entry_version)")}
        assert "file_path" in cols

    def test_v25_does_not_error_when_orm_create_all_already_added_the_column(self, temp_db):
        """A fresh install goes through Base.metadata.create_all() (the ORM
        model already declares file_path), then MigrationManager.migrate()
        for older tables -- so _apply_v25 must tolerate the column already
        being there, not just tolerate being called twice."""
        mgr = MigrationManager(temp_db)
        mgr.migrate(target_version=24)
        # Simulate what ORM create_all() would have already done.
        temp_db.execute("ALTER TABLE entry_version ADD COLUMN file_path TEXT")
        temp_db.commit()

        mgr.migrate()  # must not raise (duplicate column)

        assert mgr.get_current_version() == CURRENT_VERSION
