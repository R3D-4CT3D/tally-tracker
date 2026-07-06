"""debts.color, debts.icon -- Monopoly property-card symmetry with Goal

Revision ID: 4e2f8b6c9a1d
Revises: aa90a1ee877c
Create Date: 2026-07-07 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e2f8b6c9a1d"
down_revision: str | None = "aa90a1ee877c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("debts", sa.Column("icon", sa.String(length=32), nullable=True))
    op.add_column("debts", sa.Column("color", sa.String(length=7), nullable=True))


def downgrade() -> None:
    op.drop_column("debts", "color")
    op.drop_column("debts", "icon")
