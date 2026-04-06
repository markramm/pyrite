"""Tests for EdgeEndpoint ORM model and migration v16."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from pyrite.storage.migrations import (
    CURRENT_VERSION,
    MIGRATIONS,
    MigrationManager,
)
from pyrite.storage.models import EdgeEndpoint


@pytest.fixture
def temp_db():
    """Create a temporary database with base schema for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
    db_path.unlink()


@pytest.fixture
def migrated_db(temp_db):
    """Database with all migrations applied."""
    mgr = MigrationManager(temp_db)
    mgr.migrate()
    return temp_db


class TestEdgeEndpointModel:
    """Tests for EdgeEndpoint ORM model."""

    def test_instantiate_with_all_fields(self):
        """EdgeEndpoint model can be instantiated with all required fields."""
        ep = EdgeEndpoint(
            edge_entry_id="edge-001",
            edge_entry_kb="test-kb",
            role="source",
            field_name="owner",
            endpoint_id="person-001",
            endpoint_kb="test-kb",
            edge_type="ownership",
        )
        assert ep.edge_entry_id == "edge-001"
        assert ep.edge_entry_kb == "test-kb"
        assert ep.role == "source"
        assert ep.field_name == "owner"
        assert ep.endpoint_id == "person-001"
        assert ep.endpoint_kb == "test-kb"
        assert ep.edge_type == "ownership"

    def test_tablename(self):
        """EdgeEndpoint has correct table name."""
        assert EdgeEndpoint.__tablename__ == "edge_endpoint"


class TestMigrationV16:
    """Tests for migration v16 (edge_endpoint table)."""

    def test_migration_v16_exists(self):
        """Migration v16 exists in MIGRATIONS list."""
        v16 = [m for m in MIGRATIONS if m.version == 16]
        assert len(v16) == 1
        assert "edge_endpoint" in v16[0].description.lower()

    def test_current_version_includes_edge_endpoint_migration(self):
        """CURRENT_VERSION is at least 16 (edge endpoint migration)."""
        assert CURRENT_VERSION >= 16

    def test_migration_applies_cleanly(self, temp_db):
        """Migrations apply cleanly on a fresh database, including v16-17."""
        mgr = MigrationManager(temp_db)
        applied = mgr.migrate()
        assert mgr.get_current_version() >= 17
        assert any(m.version == 17 for m in applied)

    def test_creates_edge_endpoint_table(self, migrated_db):
        """Migration v16 creates the edge_endpoint table."""
        row = migrated_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='edge_endpoint'"
        ).fetchone()
        assert row is not None

    def test_table_has_correct_columns(self, migrated_db):
        """edge_endpoint table has all expected columns."""
        columns = {
            row["name"]
            for row in migrated_db.execute("PRAGMA table_info(edge_endpoint)").fetchall()
        }
        expected = {
            "id",
            "edge_entry_id",
            "edge_entry_kb",
            "role",
            "field_name",
            "endpoint_id",
            "endpoint_kb",
            "edge_type",
            "created_at",
        }
        assert expected == columns

    def test_indexes_exist(self, migrated_db):
        """The three indexes exist after migration."""
        indexes = {
            row["name"]
            for row in migrated_db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='edge_endpoint'"
            ).fetchall()
        }
        assert "idx_edge_endpoint_edge" in indexes
        assert "idx_edge_endpoint_target" in indexes
        assert "idx_edge_endpoint_type" in indexes

    def test_cascade_delete(self, migrated_db):
        """EdgeEndpoint entries cascade-delete when their parent entry is deleted."""
        migrated_db.execute("PRAGMA foreign_keys = ON")
        # Create base tables that v1 baseline assumes already exist
        migrated_db.executescript("""
            CREATE TABLE IF NOT EXISTS kb (
                name TEXT PRIMARY KEY,
                kb_type TEXT NOT NULL,
                path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entry (
                id TEXT NOT NULL,
                kb_name TEXT NOT NULL REFERENCES kb(name) ON DELETE CASCADE,
                entry_type TEXT NOT NULL,
                title TEXT NOT NULL,
                PRIMARY KEY (id, kb_name)
            );
        """)
        # Insert a KB and entry as parent
        migrated_db.execute(
            "INSERT INTO kb (name, kb_type, path) VALUES ('test-kb', 'zettelkasten', '/tmp')"
        )
        migrated_db.execute(
            "INSERT INTO entry (id, kb_name, entry_type, title) "
            "VALUES ('edge-001', 'test-kb', 'edge', 'Test Edge')"
        )
        # Insert an edge_endpoint referencing the entry
        migrated_db.execute(
            "INSERT INTO edge_endpoint (edge_entry_id, edge_entry_kb, role, field_name, "
            "endpoint_id, endpoint_kb, edge_type) "
            "VALUES ('edge-001', 'test-kb', 'source', 'owner', 'person-001', 'test-kb', 'ownership')"
        )
        migrated_db.commit()

        # Verify the edge_endpoint exists
        count = migrated_db.execute("SELECT COUNT(*) FROM edge_endpoint").fetchone()[0]
        assert count == 1

        # Delete the parent entry
        migrated_db.execute("DELETE FROM entry WHERE id = 'edge-001' AND kb_name = 'test-kb'")
        migrated_db.commit()

        # Verify cascade delete
        count = migrated_db.execute("SELECT COUNT(*) FROM edge_endpoint").fetchone()[0]
        assert count == 0

    def test_rollback_drops_table(self, migrated_db):
        """Rolling back v16 drops the edge_endpoint table."""
        mgr = MigrationManager(migrated_db)
        mgr.rollback(target_version=15)

        row = migrated_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='edge_endpoint'"
        ).fetchone()
        assert row is None
