"""m3 import pipeline

Revision ID: 4817a082abfe
Revises: 3d10e87f2d7b
Create Date: 2026-07-04 00:16:30.179997

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4817a082abfe"
down_revision: str | None = "3d10e87f2d7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("column_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("date_format", sa.String(length=10), nullable=False),
        sa.Column("source_hint", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_import_profiles_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_profiles")),
    )
    op.create_index(
        op.f("ix_import_profiles_household_id"), "import_profiles", ["household_id"], unique=False
    )

    op.create_table(
        "import_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_profile_id", sa.UUID(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("skipped_dupes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_import_batches_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_profile_id"],
            ["import_profiles.id"],
            name=op.f("fk_import_batches_source_profile_id_import_profiles"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_import_batches_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
    )
    op.create_index(
        op.f("ix_import_batches_household_id"), "import_batches", ["household_id"], unique=False
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("match_type", sa.String(length=20), nullable=False),
        sa.Column("match_value", sa.String(length=200), nullable=False),
        sa.Column("amount_min", sa.BigInteger(), nullable=True),
        sa.Column("amount_max", sa.BigInteger(), nullable=True),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("set_category_id", sa.UUID(), nullable=False),
        sa.Column("set_display_name", sa.String(length=500), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_rules_account_id_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_rules_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["set_category_id"],
            ["categories.id"],
            name=op.f("fk_rules_set_category_id_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rules")),
    )
    op.create_index(
        "ix_rules_household_priority", "rules", ["household_id", "priority"], unique=False
    )

    op.add_column("transactions", sa.Column("import_batch_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_transactions_import_batch_id_import_batches"),
        "transactions",
        "import_batches",
        ["import_batch_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_transactions_import_batch", "transactions", ["import_batch_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_import_batch", table_name="transactions")
    op.drop_constraint(
        op.f("fk_transactions_import_batch_id_import_batches"),
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "import_batch_id")

    op.drop_index("ix_rules_household_priority", table_name="rules")
    op.drop_table("rules")

    op.drop_index(op.f("ix_import_batches_household_id"), table_name="import_batches")
    op.drop_table("import_batches")

    op.drop_index(op.f("ix_import_profiles_household_id"), table_name="import_profiles")
    op.drop_table("import_profiles")
