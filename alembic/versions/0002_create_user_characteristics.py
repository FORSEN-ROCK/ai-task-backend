"""Создаёт таблицу характеристик пользователей."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт таблицу характеристик со ссылкой на профиль."""
    op.create_table(
        "user_characteristics",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("minor_goal", sa.Text(), nullable=True),
        sa.Column("major_goal", sa.Text(), nullable=True),
        sa.Column(
            "completed_subtasks",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("initiative", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    """Удаляет таблицу характеристик."""
    op.drop_table("user_characteristics")
