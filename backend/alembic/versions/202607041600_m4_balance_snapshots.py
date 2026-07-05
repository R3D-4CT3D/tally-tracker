"""m4 balance snapshots

Revision ID: f2995db7da64
Revises: bebb90ad6957
Create Date: 2026-07-04 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2995db7da64"
down_revision: str | None = "bebb90ad6957"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "balance_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("cash_cents", sa.BigInteger(), nullable=False),
        sa.Column("debt_cents", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_balance_snapshots_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_balance_snapshots")),
        sa.UniqueConstraint(
            "household_id", "date", name=op.f("uq_balance_snapshots_household_id")
        ),
    )
    op.create_index(
        "ix_balance_snapshots_household_date",
        "balance_snapshots",
        ["household_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_balance_snapshots_household_date", table_name="balance_snapshots")
    op.drop_table("balance_snapshots")
