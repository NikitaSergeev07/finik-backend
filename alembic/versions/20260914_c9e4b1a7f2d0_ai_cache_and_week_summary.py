"""кэш ИИ и текст итога недели

Revision ID: c9e4b1a7f2d0
Revises: 56aa5329afea
Create Date: 2026-09-14 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9e4b1a7f2d0"
down_revision: str | None = "56aa5329afea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("weeks", sa.Column("summary_text", sa.Text(), nullable=True))
    op.create_table(
        "ai_cache",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("player_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name=op.f("fk_ai_cache_player_id_players"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_ai_cache")),
    )
    op.create_index(op.f("ix_ai_cache_player_id"), "ai_cache", ["player_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_cache_player_id"), table_name="ai_cache")
    op.drop_table("ai_cache")
    op.drop_column("weeks", "summary_text")
