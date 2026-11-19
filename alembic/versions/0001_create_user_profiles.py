"""Создаёт таблицу профилей пользователей."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт таблицу профилей с предпочтениями в JSONB."""
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "preferences",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    """Удаляет таблицу профилей."""
    op.drop_table("user_profiles")
