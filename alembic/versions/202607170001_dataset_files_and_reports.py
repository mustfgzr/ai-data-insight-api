"""add dataset files and report workflow tables

Revision ID: 202607170001
Revises: 202607100001
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202607170001"
down_revision: Union[str, None] = "202607100001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_files_id", "dataset_files", ["id"])
    op.create_index("ix_dataset_files_dataset_id", "dataset_files", ["dataset_id"], unique=True)
    op.create_index("ix_dataset_files_checksum", "dataset_files", ["checksum"])

    with op.batch_alter_table("data_analyses") as batch_op:
        batch_op.add_column(sa.Column("dataset_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("analysis_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("chart_data", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("quality_issues", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_data_analyses_dataset_id",
            "datasets",
            ["dataset_id"],
            ["id"],
        )
        batch_op.create_index("ix_data_analyses_dataset_id", ["dataset_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_id", "reports", ["id"])
    op.create_index("ix_reports_user_id", "reports", ["user_id"])

    op.create_table(
        "report_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.ForeignKeyConstraint(["analysis_id"], ["data_analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "analysis_id", name="uq_report_analyses_report_analysis"),
    )
    op.create_index("ix_report_analyses_id", "report_analyses", ["id"])
    op.create_index("ix_report_analyses_report_id", "report_analyses", ["report_id"])
    op.create_index("ix_report_analyses_analysis_id", "report_analyses", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("report_analyses")
    op.drop_table("reports")
    with op.batch_alter_table("data_analyses") as batch_op:
        batch_op.drop_index("ix_data_analyses_dataset_id")
        batch_op.drop_constraint("fk_data_analyses_dataset_id", type_="foreignkey")
        batch_op.drop_column("summary")
        batch_op.drop_column("quality_issues")
        batch_op.drop_column("chart_data")
        batch_op.drop_column("status")
        batch_op.drop_column("analysis_type")
        batch_op.drop_column("dataset_id")
    op.drop_table("dataset_files")
