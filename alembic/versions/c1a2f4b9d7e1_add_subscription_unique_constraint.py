"""add subscription unique constraint

Revision ID: c1a2f4b9d7e1
Revises: bb2e2ce852df
Create Date: 2026-04-11 03:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a2f4b9d7e1"
down_revision: Union[str, Sequence[str], None] = "bb2e2ce852df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the oldest row per (chat, list) before applying uniqueness.
    op.execute(
        """
        DELETE FROM subscriptions s
        USING subscriptions d
        WHERE s.id > d.id
          AND s.tg_chat_id = d.tg_chat_id
          AND s.clickup_list_id = d.clickup_list_id
        """
    )

    op.create_unique_constraint(
        "uq_subscription_chat_list",
        "subscriptions",
        ["tg_chat_id", "clickup_list_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_subscription_chat_list", "subscriptions", type_="unique")
