"""Initial schema with ORM tables and FTS5 virtual tables.

Revision ID: 001
Revises: None
Create Date: 2026-02-21

This migration represents the baseline schema. For databases that already
exist (pre-Alembic), PyriteDB stamps this as head without running it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ORM tables are created by Base.metadata.create_all() in PyriteDB.__init__
    # This migration exists to establish the Alembic version baseline.

    # FTS5 virtual table and triggers (raw SQL, no ORM equivalent)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entry_fts USING fts5(
            id, kb_name, entry_type, title, body, summary, location,
            content='entry', content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS entry_ai AFTER INSERT ON entry BEGIN
            INSERT INTO entry_fts(rowid, id, kb_name, entry_type, title, body, summary, location)
            VALUES (new.rowid, new.id, new.kb_name, new.entry_type, new.title,
                    COALESCE(new.body, ''), COALESCE(new.summary, ''), COALESCE(new.location, ''));
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS entry_ad AFTER DELETE ON entry BEGIN
            INSERT INTO entry_fts(entry_fts, rowid, id, kb_name, entry_type, title, body, summary, location)
            VALUES('delete', old.rowid, old.id, old.kb_name, old.entry_type, old.title,
                   COALESCE(old.body, ''), COALESCE(old.summary, ''), COALESCE(old.location, ''));
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS entry_au AFTER UPDATE ON entry BEGIN
            INSERT INTO entry_fts(entry_fts, rowid, id, kb_name, entry_type, title, body, summary, location)
            VALUES('delete', old.rowid, old.id, old.kb_name, old.entry_type, old.title,
                   COALESCE(old.body, ''), COALESCE(old.summary, ''), COALESCE(old.location, ''));
            INSERT INTO entry_fts(rowid, id, kb_name, entry_type, title, body, summary, location)
            VALUES (new.rowid, new.id, new.kb_name, new.entry_type, new.title,
                    COALESCE(new.body, ''), COALESCE(new.summary, ''), COALESCE(new.location, ''));
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS entry_au")
    op.execute("DROP TRIGGER IF EXISTS entry_ad")
    op.execute("DROP TRIGGER IF EXISTS entry_ai")
    op.execute("DROP TABLE IF EXISTS entry_fts")
