"""add task state cache

Revision ID: d7f5f8d2a4c3
Revises: c1a2f4b9d7e1
Create Date: 2026-04-11 03:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7f5f8d2a4c3"
down_revision: Union[str, Sequence[str], None] = "c1a2f4b9d7e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_state_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("state_hash", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "field_name", name="uq_task_state_field"),
    )


def downgrade() -> None:
    op.drop_table("task_state_cache")
