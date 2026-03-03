"""Add protocol columns to entry table (ADR-0017).

Revision ID: 005
Revises: 004
Create Date: 2026-03-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "005"
down_revision: str = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Assignable protocol
    op.execute("ALTER TABLE entry ADD COLUMN assignee TEXT")
    op.execute("ALTER TABLE entry ADD COLUMN assigned_at TEXT")

    # Prioritizable protocol
    op.execute("ALTER TABLE entry ADD COLUMN priority INTEGER")

    # Temporal protocol (date, status, location already exist)
    op.execute("ALTER TABLE entry ADD COLUMN due_date TEXT")
    op.execute("ALTER TABLE entry ADD COLUMN start_date TEXT")
    op.execute("ALTER TABLE entry ADD COLUMN end_date TEXT")

    # Locatable protocol (location already exists)
    op.execute("ALTER TABLE entry ADD COLUMN coordinates TEXT")

    # Indexes for common query patterns
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_assignee ON entry(assignee)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_priority ON entry(priority)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_due_date ON entry(due_date)")


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN before 3.35.0
    # For safety, we do nothing on downgrade
    pass
