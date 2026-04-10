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
CURRENT_VERSION = 20


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
    Migration(
        version=6,
        description="Add local_user and session tables for web authentication",
        up="""
        CREATE TABLE IF NOT EXISTS local_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'read',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES local_user(id) ON DELETE CASCADE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            last_used TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_session_token ON session(token_hash);
        CREATE INDEX IF NOT EXISTS idx_session_user ON session(user_id);
        CREATE INDEX IF NOT EXISTS idx_session_expires ON session(expires_at);
        CREATE INDEX IF NOT EXISTS idx_local_user_username ON local_user(username);
        """,
        down="""
        DROP TABLE IF EXISTS session;
        DROP TABLE IF EXISTS local_user;
        """,
    ),
    Migration(
        version=7,
        description="Add OAuth columns to local_user for GitHub OAuth",
        # NOTE: up SQL is empty because columns may already exist from ORM create_all.
        # The actual ALTER is handled conditionally in _apply_migration_v7().
        up="",
        down="""
        DROP INDEX IF EXISTS idx_local_user_provider;
        -- SQLite does not support DROP COLUMN before 3.35; columns remain but are unused.
        """,
    ),
    Migration(
        version=8,
        description="Add kb_permission table and ephemeral_kb_count column",
        up="""
        CREATE TABLE IF NOT EXISTS kb_permission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES local_user(id) ON DELETE CASCADE,
            kb_name TEXT NOT NULL,
            role TEXT NOT NULL,
            granted_by INTEGER REFERENCES local_user(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, kb_name)
        );
        CREATE INDEX IF NOT EXISTS idx_kb_permission_user ON kb_permission(user_id);
        CREATE INDEX IF NOT EXISTS idx_kb_permission_kb ON kb_permission(kb_name);
        """,
        down="""
        DROP TABLE IF EXISTS kb_permission;
        """,
    ),
    Migration(
        version=9,
        description="Add protocol columns for ADR-0017 entry protocol mixins",
        # Actual ALTER TABLE handled conditionally in _apply_v9() since columns
        # may already exist from ORM create_all.
        up="",
        down="""
        -- SQLite < 3.35 does not support DROP COLUMN; columns remain but are unused.
        DROP INDEX IF EXISTS idx_entry_assignee;
        DROP INDEX IF EXISTS idx_entry_priority;
        DROP INDEX IF EXISTS idx_entry_due_date;
        """,
    ),
    Migration(
        version=10,
        description="Add usage_tier column to local_user for personal KB tiers",
        # Actual ALTER TABLE handled conditionally in _apply_v10() since column
        # may already exist from ORM create_all.
        up="",
        down="""
        -- SQLite < 3.35 does not support DROP COLUMN; column remains but is unused.
        """,
    ),
    Migration(
        version=11,
        description="Add lifecycle column to entry for archive support",
        # Actual ALTER TABLE handled conditionally in _apply_v11() since column
        # may already exist from ORM create_all.
        up="",
        down="""
        DROP INDEX IF EXISTS idx_entry_lifecycle;
        -- SQLite < 3.35 does not support DROP COLUMN; column remains but is unused.
        """,
    ),
    Migration(
        version=12,
        description="Add source column to kb for DB-first registry",
        # Actual ALTER TABLE handled conditionally in _apply_v12() since column
        # may already exist from ORM create_all.
        up="",
        down="""
        -- SQLite < 3.35 does not support DROP COLUMN; column remains but is unused.
        """,
    ),
    Migration(
        version=13,
        description="Add default_role column to kb for per-KB access control",
        # Actual ALTER TABLE handled conditionally in _apply_v13() since column
        # may already exist from ORM create_all.
        up="",
        down="""
        -- SQLite < 3.35 does not support DROP COLUMN; column remains but is unused.
        """,
    ),
    Migration(
        version=14,
        description="Add GitHub token columns to local_user for web GitHub integration",
        # Actual ALTER TABLE handled conditionally in _apply_v14() since columns
        # may already exist from ORM create_all.
        up="",
        down="""
        -- SQLite < 3.35 does not support DROP COLUMN; columns remain but are unused.
        """,
    ),
    Migration(
        version=15,
        description="Add review table for QA reviews",
        up="""
        CREATE TABLE IF NOT EXISTS review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            kb_name TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            reviewer_type TEXT NOT NULL,
            result TEXT NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id, kb_name) REFERENCES entry(id, kb_name) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_review_entry ON review(entry_id, kb_name);
        CREATE INDEX IF NOT EXISTS idx_review_content_hash ON review(content_hash);
        CREATE INDEX IF NOT EXISTS idx_review_reviewer ON review(reviewer);
        """,
        down="""
        DROP TABLE IF EXISTS review;
        """,
    ),
    Migration(
        version=16,
        description="Add edge_endpoint table for typed relationship entries",
        up="""
        CREATE TABLE IF NOT EXISTS edge_endpoint (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            edge_entry_id TEXT NOT NULL,
            edge_entry_kb TEXT NOT NULL,
            role TEXT NOT NULL,
            field_name TEXT NOT NULL,
            endpoint_id TEXT NOT NULL,
            endpoint_kb TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (edge_entry_id, edge_entry_kb) REFERENCES entry(id, kb_name) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_edge_endpoint_edge ON edge_endpoint(edge_entry_id, edge_entry_kb);
        CREATE INDEX IF NOT EXISTS idx_edge_endpoint_target ON edge_endpoint(endpoint_id, endpoint_kb);
        CREATE INDEX IF NOT EXISTS idx_edge_endpoint_type ON edge_endpoint(edge_type, edge_entry_kb);
        """,
        down="""
        DROP TABLE IF EXISTS edge_endpoint;
        """,
    ),
    Migration(
        version=17,
        description="Add worktree table for multi-user collaboration",
        up="""
        CREATE TABLE IF NOT EXISTS worktree (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            kb_name TEXT NOT NULL,
            repo_path TEXT NOT NULL,
            branch TEXT NOT NULL,
            worktree_path TEXT NOT NULL,
            diff_db_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            submitted_at TEXT,
            merged_at TEXT,
            rejected_at TEXT,
            feedback TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, kb_name)
        );
        CREATE INDEX IF NOT EXISTS idx_worktree_user ON worktree(user_id);
        CREATE INDEX IF NOT EXISTS idx_worktree_kb ON worktree(kb_name);
        CREATE INDEX IF NOT EXISTS idx_worktree_status ON worktree(status);
        """,
        down="""
        DROP TABLE IF EXISTS worktree;
        """,
    ),
    Migration(
        version=18,
        description="Add invite_code table for invitation-only registration",
        up="""
        CREATE TABLE IF NOT EXISTS invite_code (
            code TEXT PRIMARY KEY,
            created_by TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            used_by TEXT,
            used_at TEXT,
            role TEXT DEFAULT 'write',
            note TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_invite_code_used ON invite_code(used_by);
        """,
        down="""
        DROP TABLE IF EXISTS invite_code;
        """,
    ),
    Migration(
        version=19,
        description="Add user_api_key table for BYOK per-user LLM API keys",
        up="""
        CREATE TABLE IF NOT EXISTS user_api_key (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            encrypted_key TEXT NOT NULL,
            model TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, provider)
        );
        CREATE INDEX IF NOT EXISTS idx_user_api_key_user ON user_api_key(user_id);
        """,
        down="""
        DROP TABLE IF EXISTS user_api_key;
        """,
    ),
    Migration(
        version=20,
        description="Add fips and state columns to entry for geographic filtering",
        # Actual ALTER TABLE handled conditionally in _apply_v20() since columns
        # may already exist from ORM create_all.
        up="",
        down="""
        DROP INDEX IF EXISTS idx_entry_fips;
        DROP INDEX IF EXISTS idx_entry_state;
        -- SQLite < 3.35 does not support DROP COLUMN; columns remain but are unused.
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
            # Version-specific handlers for migrations that can't use plain SQL
            handler = getattr(self, f"_apply_v{migration.version}", None)
            if handler:
                handler()

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

    def _apply_v7(self) -> None:
        """Conditionally add OAuth columns to local_user (may already exist from ORM)."""
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(local_user)").fetchall()}
        if "auth_provider" not in existing:
            self.conn.execute(
                "ALTER TABLE local_user ADD COLUMN auth_provider TEXT DEFAULT 'local'"
            )
        if "provider_id" not in existing:
            self.conn.execute("ALTER TABLE local_user ADD COLUMN provider_id TEXT")
        if "avatar_url" not in existing:
            self.conn.execute("ALTER TABLE local_user ADD COLUMN avatar_url TEXT")
        self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_local_user_provider
                ON local_user(auth_provider, provider_id)
                WHERE provider_id IS NOT NULL
        """)
        self.conn.commit()

    def _apply_v8(self) -> None:
        """Conditionally add ephemeral_kb_count column to local_user."""
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(local_user)").fetchall()}
        if "ephemeral_kb_count" not in existing:
            self.conn.execute(
                "ALTER TABLE local_user ADD COLUMN ephemeral_kb_count INTEGER DEFAULT 0"
            )
        self.conn.commit()

    def _apply_v9(self) -> None:
        """Conditionally add protocol columns to entry (ADR-0017)."""
        # Check if entry table exists (migration tests use bare connections)
        table_exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entry'"
        ).fetchone()
        if not table_exists:
            return
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(entry)").fetchall()}
        new_columns = {
            "assignee": "TEXT",
            "assigned_at": "TEXT",
            "priority": "INTEGER",
            "due_date": "TEXT",
            "start_date": "TEXT",
            "end_date": "TEXT",
            "coordinates": "TEXT",
        }
        for col_name, col_type in new_columns.items():
            if col_name not in existing:
                self.conn.execute(f"ALTER TABLE entry ADD COLUMN {col_name} {col_type}")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_assignee ON entry(assignee)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_priority ON entry(priority)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_due_date ON entry(due_date)")
        self.conn.commit()

    def _apply_v10(self) -> None:
        """Conditionally add usage_tier column to local_user."""
        table_exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='local_user'"
        ).fetchone()
        if not table_exists:
            return
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(local_user)").fetchall()}
        if "usage_tier" not in existing:
            self.conn.execute("ALTER TABLE local_user ADD COLUMN usage_tier TEXT DEFAULT 'default'")
        self.conn.commit()

    def _apply_v11(self) -> None:
        """Conditionally add lifecycle column to entry for archive support."""
        table_exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entry'"
        ).fetchone()
        if not table_exists:
            return
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(entry)").fetchall()}
        if "lifecycle" not in existing:
            self.conn.execute("ALTER TABLE entry ADD COLUMN lifecycle TEXT DEFAULT 'active'")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_lifecycle ON entry(lifecycle)")
        self.conn.commit()

    def _apply_v12(self) -> None:
        """Conditionally add source column to kb for DB-first registry."""
        table_exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='kb'"
        ).fetchone()
        if not table_exists:
            return
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(kb)").fetchall()}
        if "source" not in existing:
            self.conn.execute("ALTER TABLE kb ADD COLUMN source TEXT DEFAULT 'user'")
        self.conn.commit()

    def _apply_v14(self) -> None:
        """Conditionally add GitHub token columns to local_user."""
        table_exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='local_user'"
        ).fetchone()
        if not table_exists:
            return
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(local_user)").fetchall()}
        if "github_access_token" not in existing:
            self.conn.execute("ALTER TABLE local_user ADD COLUMN github_access_token TEXT")
        if "github_token_scopes" not in existing:
            self.conn.execute("ALTER TABLE local_user ADD COLUMN github_token_scopes TEXT")
        self.conn.commit()

    def _apply_v13(self) -> None:
        """Conditionally add default_role column to kb for per-KB access control."""
        table_exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='kb'"
        ).fetchone()
        if not table_exists:
            return
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(kb)").fetchall()}
        if "default_role" not in existing:
            self.conn.execute("ALTER TABLE kb ADD COLUMN default_role TEXT")
        self.conn.commit()

    def _apply_v20(self) -> None:
        """Conditionally add fips and state columns to entry for geographic filtering."""
        table_exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entry'"
        ).fetchone()
        if not table_exists:
            return
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(entry)").fetchall()}
        if "fips" not in existing:
            self.conn.execute("ALTER TABLE entry ADD COLUMN fips TEXT")
        if "state" not in existing:
            self.conn.execute("ALTER TABLE entry ADD COLUMN state TEXT")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_fips ON entry(fips)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_state ON entry(state)")
        self.conn.commit()

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
