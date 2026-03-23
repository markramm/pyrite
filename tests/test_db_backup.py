"""Tests for pyrite db backup and pyrite db restore CLI commands."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository

runner = CliRunner()


@pytest.fixture
def db_env():
    """Environment with a populated PyriteDB for backup/restore tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        events_path = tmpdir / "events"
        events_path.mkdir()

        events_kb = KBConfig(
            name="test-events",
            path=events_path,
            kb_type=KBType.EVENTS,
            description="Test events KB",
        )

        config = PyriteConfig(
            knowledge_bases=[events_kb],
            settings=Settings(index_path=db_path),
        )

        # Create sample data
        events_repo = KBRepository(events_kb)
        for i in range(3):
            event = EventEntry.create(
                date=f"2025-01-{10 + i:02d}",
                title=f"Test Event {i}",
                body=f"Body for event {i} about testing.",
                importance=5 + i,
            )
            event.tags = ["test", "backup"]
            events_repo.save(event)

        db = PyriteDB(db_path)
        IndexManager(db, config).index_all()
        db.close()

        yield {
            "config": config,
            "tmpdir": tmpdir,
            "db_path": db_path,
        }


def _patch_config(env):
    """Patch load_config so CLI commands use our test config."""
    target = env["config"]
    return patch("pyrite.cli.db_commands.load_config", return_value=target)


@pytest.mark.cli
class TestDBBackup:
    def test_backup_creates_file(self, db_env):
        """pyrite db backup --output <path> creates a .db file at the specified path."""
        output_path = db_env["tmpdir"] / "my-backup.db"
        with _patch_config(db_env):
            result = runner.invoke(app, ["db", "backup", "--output", str(output_path)])
            assert result.exit_code == 0, result.output
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_backup_default_path(self, db_env):
        """Without --output, creates backup with timestamp in current dir."""
        with _patch_config(db_env):
            # Use the tmpdir as working directory via monkeypatch isn't easy with
            # CliRunner, so we just check the output mentions the backup path
            result = runner.invoke(app, ["db", "backup"])
            assert result.exit_code == 0, result.output
            assert "pyrite-backup-" in result.output

    def test_backup_file_is_valid_sqlite(self, db_env):
        """Backup file is a valid SQLite database."""
        output_path = db_env["tmpdir"] / "valid-check.db"
        with _patch_config(db_env):
            result = runner.invoke(app, ["db", "backup", "--output", str(output_path)])
            assert result.exit_code == 0, result.output

        # Verify it's a valid SQLite DB by opening and querying
        conn = sqlite3.connect(str(output_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert len(tables) > 0

    def test_backup_includes_all_tables(self, db_env):
        """Backup contains the same tables as the original."""
        output_path = db_env["tmpdir"] / "tables-check.db"
        with _patch_config(db_env):
            result = runner.invoke(app, ["db", "backup", "--output", str(output_path)])
            assert result.exit_code == 0, result.output

        # Get tables from original
        orig_conn = sqlite3.connect(str(db_env["db_path"]))
        orig_tables = {
            row[0]
            for row in orig_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        orig_conn.close()

        # Get tables from backup
        backup_conn = sqlite3.connect(str(output_path))
        backup_tables = {
            row[0]
            for row in backup_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        backup_conn.close()

        assert orig_tables == backup_tables


@pytest.mark.cli
class TestDBRestore:
    def test_restore_from_backup(self, db_env):
        """pyrite db restore <path> --force replaces the current DB."""
        # First create a backup
        backup_path = db_env["tmpdir"] / "restore-test.db"
        with _patch_config(db_env):
            result = runner.invoke(app, ["db", "backup", "--output", str(backup_path)])
            assert result.exit_code == 0, result.output

        # Now restore from it
        with _patch_config(db_env):
            result = runner.invoke(app, ["db", "restore", str(backup_path), "--force"])
            assert result.exit_code == 0, result.output
            assert "Restored" in result.output or "restored" in result.output

        # Verify the DB is valid after restore
        conn = sqlite3.connect(str(db_env["db_path"]))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert len(tables) > 0

    def test_restore_nonexistent_file(self, db_env):
        """Restore with a bad path gives a clear error and exit 1."""
        with _patch_config(db_env):
            result = runner.invoke(
                app, ["db", "restore", "/tmp/nonexistent-backup-xyz.db", "--force"]
            )
            assert result.exit_code == 1
            assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    def test_restore_invalid_file(self, db_env):
        """Restore with a non-SQLite file gives a clear error."""
        bad_file = db_env["tmpdir"] / "not-a-db.txt"
        bad_file.write_text("this is not a sqlite database")
        with _patch_config(db_env):
            result = runner.invoke(app, ["db", "restore", str(bad_file), "--force"])
            assert result.exit_code == 1
            assert "not a valid" in result.output.lower() or "invalid" in result.output.lower()

    def test_restore_without_force(self, db_env):
        """Restore without --force should warn and exit."""
        backup_path = db_env["tmpdir"] / "no-force-test.db"
        with _patch_config(db_env):
            runner.invoke(app, ["db", "backup", "--output", str(backup_path)])
            result = runner.invoke(app, ["db", "restore", str(backup_path)])
            assert result.exit_code == 1
            assert "force" in result.output.lower()
