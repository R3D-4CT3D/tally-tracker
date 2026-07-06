"""csv import fixes -- last_four, auto_categorized_count, fees category

Revision ID: aa90a1ee877c
Revises: a04cede125c0
Create Date: 2026-07-06 09:00:00.000000

"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from uuid6 import uuid7

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa90a1ee877c"
down_revision: str | None = "a04cede125c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FEES_CATEGORY = {"name": "Fees", "icon": "🧾", "color": "#78716C"}


def upgrade() -> None:
    op.add_column("accounts", sa.Column("last_four", sa.String(length=4), nullable=True))
    op.add_column(
        "import_batches",
        sa.Column("auto_categorized_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Backfill: every existing household is missing the newly-added "Fees"
    # default category (it's only seeded at /setup time going forward --
    # see app/services/categories.py's DEFAULT_CATEGORIES). New households
    # get it automatically; this is a one-time catch-up for existing ones.
    bind = op.get_bind()
    household_ids = bind.execute(sa.text("SELECT id FROM households")).scalars().all()
    now = datetime.now(UTC)
    for household_id in household_ids:
        already_has_fees = bind.execute(
            sa.text(
                "SELECT 1 FROM categories WHERE household_id = :household_id AND name = :name"
            ),
            {"household_id": household_id, "name": _FEES_CATEGORY["name"]},
        ).first()
        if already_has_fees is not None:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO categories "
                "(id, household_id, name, parent_id, icon, color, is_system, "
                "created_at, updated_at) "
                "VALUES (:id, :household_id, :name, NULL, :icon, :color, true, :now, :now)"
            ),
            {
                "id": uuid.UUID(str(uuid7())),
                "household_id": household_id,
                "name": _FEES_CATEGORY["name"],
                "icon": _FEES_CATEGORY["icon"],
                "color": _FEES_CATEGORY["color"],
                "now": now,
            },
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM categories WHERE name = 'Fees' AND is_system = true"))
    op.drop_column("import_batches", "auto_categorized_count")
    op.drop_column("accounts", "last_four")
