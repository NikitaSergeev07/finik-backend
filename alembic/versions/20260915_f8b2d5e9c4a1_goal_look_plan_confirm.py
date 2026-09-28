"""каталог мечты, цвет ростка, утверждение плана

Revision ID: f8b2d5e9c4a1
Revises: e7a1c4d8b3f2
Create Date: 2026-09-15 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f8b2d5e9c4a1"
down_revision: str | None = "e7a1c4d8b3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pets",
        sa.Column("look_variant", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "weeks",
        sa.Column("plan_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "goals",
        sa.Column("catalog_slug", sa.String(length=40), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("goals", "catalog_slug")
    op.drop_column("weeks", "plan_confirmed")
    op.drop_column("pets", "look_variant")
