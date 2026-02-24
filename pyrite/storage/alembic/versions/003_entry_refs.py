"""Add entry_ref table for typed object references.

Revision ID: 003
Revises: 002
Create Date: 2026-02-23

Adds entry_ref table to index object-ref field types from KB schemas,
enabling reverse lookups like "which entries reference this entry".
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS entry_ref (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            source_kb TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_kb TEXT NOT NULL,
            field_name TEXT NOT NULL,
            target_type TEXT,
            FOREIGN KEY (source_id, source_kb) REFERENCES entry(id, kb_name) ON DELETE CASCADE
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_ref_source ON entry_ref(source_id, source_kb)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_ref_target ON entry_ref(target_id, target_kb)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_ref_field ON entry_ref(field_name)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS entry_ref")
