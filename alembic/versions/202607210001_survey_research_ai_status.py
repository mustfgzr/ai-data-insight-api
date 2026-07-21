"""Store optional AI summary state for survey research reports.

Revision ID: 202607210001
Revises: 202607200002
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "202607210001"
down_revision = "202607200002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("survey_reports")
    }
    with op.batch_alter_table("survey_reports") as batch_op:
        if "ai_report_status" not in existing_columns:
            batch_op.add_column(
                sa.Column("ai_report_status", sa.String(), nullable=False, server_default="not_requested")
            )
        if "ai_report_warning" not in existing_columns:
            batch_op.add_column(sa.Column("ai_report_warning", sa.Text(), nullable=True))


def downgrade() -> None:
    existing_columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("survey_reports")
    }
    with op.batch_alter_table("survey_reports") as batch_op:
        if "ai_report_warning" in existing_columns:
            batch_op.drop_column("ai_report_warning")
        if "ai_report_status" in existing_columns:
            batch_op.drop_column("ai_report_status")
