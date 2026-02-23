"""Add collaboration tables: user, repo, workspace_repo, entry_version.

Revision ID: 002
Revises: 001
Create Date: 2026-02-22

Adds Phase 7 collaboration support:
- user table (GitHub identity)
- repo table (repo registry with fork tracking)
- workspace_repo table (user <-> repo membership)
- entry_version table (change history from git log)
- New columns on kb (repo_id, repo_subpath) and entry (created_by, modified_by)
- Sentinel 'local' user for non-authenticated setups
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # User table
    op.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github_login TEXT NOT NULL UNIQUE,
            github_id INTEGER NOT NULL UNIQUE,
            display_name TEXT,
            avatar_url TEXT,
            email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT
        )
    """)

    # Repo table
    op.execute("""
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
        )
    """)

    # WorkspaceRepo table
    op.execute("""
        CREATE TABLE IF NOT EXISTS workspace_repo (
            user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            repo_id INTEGER NOT NULL REFERENCES repo(id) ON DELETE CASCADE,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            role TEXT DEFAULT 'subscriber',
            auto_sync INTEGER DEFAULT 1,
            sync_interval INTEGER DEFAULT 3600,
            PRIMARY KEY (user_id, repo_id)
        )
    """)

    # EntryVersion table
    op.execute("""
        CREATE TABLE IF NOT EXISTS entry_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            kb_name TEXT NOT NULL,
            commit_hash TEXT(40) NOT NULL,
            author_name TEXT,
            author_email TEXT,
            author_github_login TEXT,
            commit_date TEXT NOT NULL,
            message TEXT,
            diff_summary TEXT,
            change_type TEXT,
            FOREIGN KEY (entry_id, kb_name) REFERENCES entry(id, kb_name) ON DELETE CASCADE
        )
    """)

    # Indexes for entry_version
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_entry_version_entry ON entry_version(entry_id, kb_name)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_version_commit ON entry_version(commit_hash)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_entry_version_author ON entry_version(author_github_login)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_version_date ON entry_version(commit_date)")

    # Index for repo name
    op.execute("CREATE INDEX IF NOT EXISTS idx_repo_name ON repo(name)")

    # Index for user github_login
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_github_login ON user(github_login)")

    # Add columns to kb table (SQLite ADD COLUMN)
    # These are idempotent — they'll fail silently if columns already exist (from ORM create_all)
    try:
        op.execute(
            "ALTER TABLE kb ADD COLUMN repo_id INTEGER REFERENCES repo(id) ON DELETE SET NULL"
        )
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE kb ADD COLUMN repo_subpath TEXT DEFAULT ''")
    except Exception:
        pass

    # Add columns to entry table
    try:
        op.execute("ALTER TABLE entry ADD COLUMN created_by TEXT")
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE entry ADD COLUMN modified_by TEXT")
    except Exception:
        pass

    # Insert sentinel 'local' user for non-authenticated setups
    op.execute("""
        INSERT OR IGNORE INTO user (github_login, github_id, display_name)
        VALUES ('local', 0, 'Local User')
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS entry_version")
    op.execute("DROP TABLE IF EXISTS workspace_repo")
    op.execute("DROP TABLE IF EXISTS repo")
    op.execute("DROP TABLE IF EXISTS user")
    # Note: SQLite does not support DROP COLUMN, so kb.repo_id, kb.repo_subpath,
    # entry.created_by, entry.modified_by will remain but be unused after downgrade.
