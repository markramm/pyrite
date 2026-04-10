"""Add fips and state columns to entry table for geographic filtering.

Revision ID: 006
Revises: 005
Create Date: 2026-04-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "006"
down_revision: str = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE entry ADD COLUMN fips TEXT")
    op.execute("ALTER TABLE entry ADD COLUMN state TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_fips ON entry(fips)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_entry_state ON entry(state)")


def downgrade() -> None:
    pass
