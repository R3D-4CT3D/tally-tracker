"""baseline

Revision ID: 202607030001
Revises:
Create Date: 2026-07-03 00:00:00

No-op baseline revision. Proves the Alembic pipeline (async engine, naming
convention, CI Postgres service) runs cleanly against a fresh database before any
real tables exist. Concrete tables (households, users, accounts, ...) land
starting M1.
"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "202607030001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
