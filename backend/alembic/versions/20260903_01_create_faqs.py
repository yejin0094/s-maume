"""create faqs table

Revision ID: 20260903_01
Revises:
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=255), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faqs_is_active", "faqs", ["is_active"])
    op.create_index("ix_faqs_question", "faqs", ["question"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_faqs_question", table_name="faqs")
    op.drop_index("ix_faqs_is_active", table_name="faqs")
    op.drop_table("faqs")
