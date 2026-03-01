"""
Schema Migration System for PyriteDB

Provides:
- Version tracking via schema_version table
- Forward migrations with rollback support
- Migration status reporting
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Current schema version
CURRENT_VERSION = 5


@dataclass
class Migration:
    """A single database migration."""

    version: int
    description: str
    up: str  # SQL to apply migration
    down: str  # SQL to rollback migration


# Migration registry - add new migrations here
MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description="Initial schema with FTS5",
        up="""
        -- Version 1 is the baseline schema (no changes needed if tables exist)
        -- This migration exists to establish version tracking
        """,
        down="""
        -- Cannot rollback below version 1
        """,
    ),
    Migration(
        version=2,
        description="Add vec_entry virtual table for vector search",
        up="""
        -- vec_entry is created conditionally by PyriteDB._run_migrations()
        -- only when sqlite-vec extension is available.
        -- This migration just records the version bump.
        """,
        down="""
        DROP TABLE IF EXISTS vec_entry;
        """,
    ),
    Migration(
        version=3,
        description="Add collaboration tables (user, repo, workspace_repo, entry_version)",
        up="""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github_login TEXT NOT NULL UNIQUE,
            github_id INTEGER NOT NULL UNIQUE,
            display_name TEXT,
            avatar_url TEXT,
            email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT
        );

        CREATE TABLE IF NOT EXISTS repo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            local_path TEXT NOT NULL,
            remote_url TEXT,
            owner TEXT,
            visibility TEXT DEFAULT 'public',
            default_branch TEXT DEFAULT 'main',
            upstream_repo_id INTEGER REFERENCES repo(id) ON DELETE SET NULL,
            is_fork INTEGER DEFAULT 0,
            last_synced_commit TEXT,
            last_synced TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workspace_repo (
            user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            repo_id INTEGER NOT NULL REFERENCES repo(id) ON DELETE CASCADE,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            role TEXT DEFAULT 'subscriber',
            auto_sync INTEGER DEFAULT 1,
            sync_interval INTEGER DEFAULT 3600,
            PRIMARY KEY (user_id, repo_id)
        );

        CREATE TABLE IF NOT EXISTS entry_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            kb_name TEXT NOT NULL,
            commit_hash TEXT NOT NULL,
            author_name TEXT,
            author_email TEXT,
            author_github_login TEXT,
            commit_date TEXT NOT NULL,
            message TEXT,
            diff_summary TEXT,
            change_type TEXT,
            FOREIGN KEY (entry_id, kb_name) REFERENCES entry(id, kb_name) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_entry_version_entry ON entry_version(entry_id, kb_name);
        CREATE INDEX IF NOT EXISTS idx_entry_version_commit ON entry_version(commit_hash);
        CREATE INDEX IF NOT EXISTS idx_entry_version_author ON entry_version(author_github_login);
        CREATE INDEX IF NOT EXISTS idx_entry_version_date ON entry_version(commit_date);
        CREATE INDEX IF NOT EXISTS idx_repo_name ON repo(name);
        CREATE INDEX IF NOT EXISTS idx_user_github_login ON user(github_login);

        INSERT OR IGNORE INTO user (github_login, github_id, display_name)
        VALUES ('local', 0, 'Local User');
        """,
        down="""
        DROP TABLE IF EXISTS entry_version;
        DROP TABLE IF EXISTS workspace_repo;
        DROP TABLE IF EXISTS repo;
        DROP TABLE IF EXISTS user;
        """,
    ),
    Migration(
        version=4,
        description="Add entry_ref table for typed object references",
        up="""
        CREATE TABLE IF NOT EXISTS entry_ref (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            source_kb TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_kb TEXT NOT NULL,
            field_name TEXT NOT NULL,
            target_type TEXT,
            FOREIGN KEY (source_id, source_kb) REFERENCES entry(id, kb_name) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_entry_ref_source ON entry_ref(source_id, source_kb);
        CREATE INDEX IF NOT EXISTS idx_entry_ref_target ON entry_ref(target_id, target_kb);
        CREATE INDEX IF NOT EXISTS idx_entry_ref_field ON entry_ref(field_name);
        """,
        down="""
        DROP TABLE IF EXISTS entry_ref;
        """,
    ),
    Migration(
        version=5,
        description="Add block table for block-level references",
        up="""
        CREATE TABLE IF NOT EXISTS block (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            kb_name TEXT NOT NULL,
            block_id TEXT NOT NULL,
            heading TEXT,
            content TEXT NOT NULL,
            position INTEGER NOT NULL,
            block_type TEXT NOT NULL,
            FOREIGN KEY (entry_id, kb_name) REFERENCES entry(id, kb_name) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_block_entry ON block(entry_id, kb_name);
        CREATE INDEX IF NOT EXISTS idx_block_block_id ON block(block_id);
        """,
        down="""
        DROP TABLE IF EXISTS block;
        """,
    ),
]


class MigrationManager:
    """
    Manages database schema migrations.

    Usage:
        db = PyriteDB(path)
        mgr = MigrationManager(db._raw_conn)
        mgr.migrate()  # Apply all pending migrations
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_version_table()

    def _ensure_version_table(self) -> None:
        """Create schema_version table if not exists."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def get_current_version(self) -> int:
        """Get the current schema version (0 if no migrations applied)."""
        row = self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row[0] is not None else 0

    def get_applied_migrations(self) -> list[dict]:
        """Get list of applied migrations."""
        rows = self.conn.execute(
            "SELECT version, description, applied_at FROM schema_version ORDER BY version"
        ).fetchall()
        return [{"version": r[0], "description": r[1], "applied_at": r[2]} for r in rows]

    def get_pending_migrations(self) -> list[Migration]:
        """Get migrations that haven't been applied yet."""
        current = self.get_current_version()
        return [m for m in MIGRATIONS if m.version > current]

    def migrate(self, target_version: int | None = None) -> list[Migration]:
        """
        Apply pending migrations up to target_version.

        Args:
            target_version: Version to migrate to (default: latest)

        Returns:
            List of applied migrations
        """
        if target_version is None:
            target_version = CURRENT_VERSION

        current = self.get_current_version()
        if current >= target_version:
            return []

        applied = []
        pending = [m for m in MIGRATIONS if current < m.version <= target_version]

        for migration in sorted(pending, key=lambda m: m.version):
            self._apply_migration(migration)
            applied.append(migration)

        return applied

    def _apply_migration(self, migration: Migration) -> None:
        """Apply a single migration."""
        try:
            # Execute the migration SQL
            if migration.up.strip():
                self.conn.executescript(migration.up)

            # Record the migration
            self.conn.execute(
                """
                INSERT INTO schema_version (version, description, applied_at)
                VALUES (?, ?, ?)
                """,
                (migration.version, migration.description, datetime.now(UTC).isoformat()),
            )
            self.conn.commit()
            logger.info("Applied migration v%d: %s", migration.version, migration.description)
        except Exception as e:
            self.conn.rollback()
            raise MigrationError(f"Failed to apply migration v{migration.version}: {e}") from e

    def rollback(self, target_version: int = 0) -> list[Migration]:
        """
        Rollback migrations down to target_version.

        Args:
            target_version: Version to rollback to (default: 0, removes all)

        Returns:
            List of rolled back migrations
        """
        current = self.get_current_version()
        if current <= target_version:
            return []

        rolled_back = []
        to_rollback = [m for m in MIGRATIONS if target_version < m.version <= current]

        for migration in sorted(to_rollback, key=lambda m: m.version, reverse=True):
            self._rollback_migration(migration)
            rolled_back.append(migration)

        return rolled_back

    def _rollback_migration(self, migration: Migration) -> None:
        """Rollback a single migration."""
        try:
            # Execute the rollback SQL
            if migration.down.strip() and "Cannot rollback" not in migration.down:
                self.conn.executescript(migration.down)

            # Remove the migration record
            self.conn.execute("DELETE FROM schema_version WHERE version = ?", (migration.version,))
            self.conn.commit()
            logger.info("Rolled back migration v%d: %s", migration.version, migration.description)
        except Exception as e:
            self.conn.rollback()
            raise MigrationError(f"Failed to rollback migration v{migration.version}: {e}") from e

    def status(self) -> dict:
        """Get migration status summary."""
        return {
            "current_version": self.get_current_version(),
            "target_version": CURRENT_VERSION,
            "applied": self.get_applied_migrations(),
            "pending": [
                {"version": m.version, "description": m.description}
                for m in self.get_pending_migrations()
            ],
            "up_to_date": self.get_current_version() >= CURRENT_VERSION,
        }


class MigrationError(Exception):
    """Raised when a migration fails."""

    pass


def ensure_migrated(db_path: Path) -> None:
    """
    Ensure database is migrated to current version.

    Call this during application startup to auto-migrate.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        mgr = MigrationManager(conn)
        pending = mgr.get_pending_migrations()
        if pending:
            logger.info("Applying %d pending migration(s)...", len(pending))
            mgr.migrate()
            logger.info("Database now at version %d", mgr.get_current_version())
    finally:
        conn.close()
