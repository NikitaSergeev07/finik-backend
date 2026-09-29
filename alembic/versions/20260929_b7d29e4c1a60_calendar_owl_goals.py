"""Calendar, isolated demo and owl appearance.

Revision ID: b7d29e4c1a60
Revises: a1c3e5f7b902
"""

import sqlalchemy as sa
from alembic import op

revision = "b7d29e4c1a60"
down_revision = "a1c3e5f7b902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players", sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC")
    )
    op.add_column(
        "players", sa.Column("mode", sa.String(12), nullable=False, server_default="normal")
    )
    op.add_column("players", sa.Column("clock", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column(
        "players",
        sa.Column(
            "selected_goal_slug", sa.String(40), nullable=False, server_default="sunny_window"
        ),
    )
    op.add_column("pets", sa.Column("accessories", sa.JSON(), nullable=False, server_default="[]"))
    op.execute("UPDATE pets SET species = 'OWL'")
    op.execute("""UPDATE players SET selected_goal_slug = COALESCE(
        (SELECT catalog_slug FROM goals WHERE goals.player_id=players.id
         ORDER BY created_at DESC LIMIT 1), 'sunny_window')""")


def downgrade() -> None:
    op.execute("UPDATE pets SET species = 'CACTUS' WHERE species = 'OWL'")
    op.drop_column("pets", "accessories")
    for name in ("selected_goal_slug", "clock", "mode", "timezone"):
        op.drop_column("players", name)
