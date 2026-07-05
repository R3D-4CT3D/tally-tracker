"""m4 bills debts goals

Revision ID: bebb90ad6957
Revises: 4817a082abfe
Create Date: 2026-07-04 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bebb90ad6957"
down_revision: str | None = "4817a082abfe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("original_balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("current_balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("apr_bps", sa.Integer(), nullable=False),
        sa.Column("min_payment_cents", sa.BigInteger(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("paid_off_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_debts_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_debts")),
    )
    op.create_index(op.f("ix_debts_household_id"), "debts", ["household_id"], unique=False)

    op.add_column("transactions", sa.Column("debt_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_transactions_debt_id_debts"),
        "transactions",
        "debts",
        ["debt_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_transactions_household_debt", "transactions", ["household_id", "debt_id"], unique=False
    )

    op.create_table(
        "bills",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=True),
        sa.Column("is_variable", sa.Boolean(), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("custom_interval_days", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("autopay", sa.Boolean(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_bills_account_id_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_bills_category_id_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_bills_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bills")),
    )
    op.create_index(op.f("ix_bills_household_id"), "bills", ["household_id"], unique=False)

    op.create_table(
        "bill_payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("bill_id", sa.UUID(), nullable=False),
        sa.Column("transaction_id", sa.UUID(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["bills.id"],
            name=op.f("fk_bill_payments_bill_id_bills"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_bill_payments_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("fk_bill_payments_transaction_id_transactions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bill_payments")),
    )
    op.create_index(
        "ix_bill_payments_household_bill",
        "bill_payments",
        ["household_id", "bill_id"],
        unique=False,
    )

    op.create_table(
        "goals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_cents", sa.BigInteger(), nullable=False),
        sa.Column("current_cents", sa.BigInteger(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("icon", sa.String(length=32), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_goals_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goals")),
    )
    op.create_index(op.f("ix_goals_household_id"), "goals", ["household_id"], unique=False)

    op.create_table(
        "goal_contributions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("goal_id", sa.UUID(), nullable=False),
        sa.Column("transaction_id", sa.UUID(), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["goals.id"],
            name=op.f("fk_goal_contributions_goal_id_goals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_goal_contributions_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("fk_goal_contributions_transaction_id_transactions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_goal_contributions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goal_contributions")),
    )
    op.create_index(
        "ix_goal_contributions_household_goal",
        "goal_contributions",
        ["household_id", "goal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_goal_contributions_household_goal", table_name="goal_contributions")
    op.drop_table("goal_contributions")

    op.drop_index(op.f("ix_goals_household_id"), table_name="goals")
    op.drop_table("goals")

    op.drop_index("ix_bill_payments_household_bill", table_name="bill_payments")
    op.drop_table("bill_payments")

    op.drop_index(op.f("ix_bills_household_id"), table_name="bills")
    op.drop_table("bills")

    op.drop_index("ix_transactions_household_debt", table_name="transactions")
    op.drop_constraint(op.f("fk_transactions_debt_id_debts"), "transactions", type_="foreignkey")
    op.drop_column("transactions", "debt_id")

    op.drop_index(op.f("ix_debts_household_id"), table_name="debts")
    op.drop_table("debts")
