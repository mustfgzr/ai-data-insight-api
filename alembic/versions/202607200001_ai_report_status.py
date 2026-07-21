"""Store optional AI report generation state.

Revision ID: 202607200001
Revises: 202607170001
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "202607200001"
down_revision = "202607170001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("data_analyses") as batch_op:
        batch_op.add_column(
            sa.Column("ai_report_status", sa.String(), nullable=False, server_default="completed")
        )
        batch_op.add_column(sa.Column("ai_report_warning", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("data_analyses") as batch_op:
        batch_op.drop_column("ai_report_warning")
        batch_op.drop_column("ai_report_status")
