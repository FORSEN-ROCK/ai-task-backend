"""Создаёт таблицы целей, задач, факторов и связей задач."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт таблицы планирования и ограничения целостности."""
    op.create_table(
        "planning_goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("available_minutes", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.CheckConstraint("available_minutes >= 0", name="ck_planning_goals_minutes"),
        sa.CheckConstraint(
            "priority BETWEEN 1 AND 5", name="ck_planning_goals_priority"
        ),
    )
    op.create_index("ix_planning_goals_user_id", "planning_goals", ["user_id"])
    op.create_table(
        "planning_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "goal_id",
            sa.Uuid(),
            sa.ForeignKey("planning_goals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "priority BETWEEN 1 AND 5", name="ck_planning_tasks_priority"
        ),
        sa.CheckConstraint("position >= 0", name="ck_planning_tasks_position"),
    )
    op.create_index("ix_planning_tasks_goal_id", "planning_tasks", ["goal_id"])
    op.create_table(
        "planning_factors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("is_short_term", sa.Boolean(), nullable=False),
        sa.Column("impact_days", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('facilitating', 'complicating')", name="ck_planning_factors_kind"
        ),
        sa.CheckConstraint("impact_days > 0", name="ck_planning_factors_impact_days"),
    )
    op.create_index("ix_planning_factors_user_id", "planning_factors", ["user_id"])
    op.create_table(
        "planning_task_dependencies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "left_task_id",
            sa.Uuid(),
            sa.ForeignKey("planning_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "right_task_id",
            sa.Uuid(),
            sa.ForeignKey("planning_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("influence", sa.String(12), nullable=False),
        sa.UniqueConstraint(
            "left_task_id", "right_task_id", name="uq_planning_dependencies_pair"
        ),
        sa.CheckConstraint(
            "left_task_id <> right_task_id", name="ck_planning_dependencies_distinct"
        ),
        sa.CheckConstraint(
            "influence IN ('blocks', 'complements', 'relates_to')",
            name="ck_planning_dependencies_influence",
        ),
    )
    op.create_index(
        "ix_planning_task_dependencies_right_task_id",
        "planning_task_dependencies",
        ["right_task_id"],
    )


def downgrade() -> None:
    """Удаляет таблицы планирования в порядке зависимостей."""
    op.drop_table("planning_task_dependencies")
    op.drop_table("planning_factors")
    op.drop_table("planning_tasks")
    op.drop_table("planning_goals")
