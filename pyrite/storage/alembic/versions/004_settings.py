"""Add settings table.

Revision ID: 004
Revises: 002
Create Date: 2026-02-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "004"
down_revision: str = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS setting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_setting_key ON setting(key)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS setting")
