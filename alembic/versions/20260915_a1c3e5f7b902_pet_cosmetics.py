"""наряды на ростке: горшок и аксессуар

Revision ID: a1c3e5f7b902
Revises: f8b2d5e9c4a1
Create Date: 2026-09-15 22:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c3e5f7b902"
down_revision: str | None = "f8b2d5e9c4a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pets",
        sa.Column("equipped_pot", sa.String(length=40), nullable=False, server_default=""),
    )
    op.add_column(
        "pets",
        sa.Column("equipped_accessory", sa.String(length=40), nullable=False, server_default=""),
    )
    op.add_column(
        "shop_items",
        sa.Column("slot", sa.String(length=20), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("shop_items", "slot")
    op.drop_column("pets", "equipped_accessory")
    op.drop_column("pets", "equipped_pot")
