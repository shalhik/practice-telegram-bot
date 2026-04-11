"""ensure sent_events table

Revision ID: f2b7c4e9a1d0
Revises: d7f5f8d2a4c3
Create Date: 2026-04-11 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2b7c4e9a1d0"
down_revision: Union[str, Sequence[str], None] = "d7f5f8d2a4c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("sent_events"):
        op.create_table(
            "sent_events",
            sa.Column("event_id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("event_id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("sent_events"):
        op.drop_table("sent_events")
