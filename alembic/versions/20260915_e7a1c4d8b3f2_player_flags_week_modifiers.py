"""флаги игрока, модификаторы недели, скрытые товары

Revision ID: e7a1c4d8b3f2
Revises: c9e4b1a7f2d0
Create Date: 2026-09-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7a1c4d8b3f2"
down_revision: str | None = "c9e4b1a7f2d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("event_mode", sa.String(length=16), nullable=False, server_default="random"),
    )
    op.add_column(
        "players",
        sa.Column("vaccinated_until", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "players",
        sa.Column(
            "unlocked_shop",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.add_column(
        "weeks",
        sa.Column(
            "modifiers",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "shop_items",
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("shop_items", "hidden")
    op.drop_column("weeks", "modifiers")
    op.drop_column("players", "unlocked_shop")
    op.drop_column("players", "vaccinated_until")
    op.drop_column("players", "event_mode")
