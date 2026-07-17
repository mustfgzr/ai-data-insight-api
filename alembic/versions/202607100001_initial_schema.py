"""initial schema

Revision ID: 202607100001
Revises:
Create Date: 2026-07-10
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202607100001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyses_id", "analyses", ["id"])

    op.create_table(
        "data_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("template", sa.String(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("columns_info", sa.Text(), nullable=True),
        sa.Column("statistics", sa.Text(), nullable=True),
        sa.Column("ai_report", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_analyses_id", "data_analyses", ["id"])

    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("detected_format", sa.String(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datasets_id", "datasets", ["id"])
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])

    op.create_table(
        "dataset_columns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column("dtype", sa.String(), nullable=False),
        sa.Column("semantic_type", sa.String(), nullable=True),
        sa.Column("missing_count", sa.Integer(), nullable=True),
        sa.Column("missing_pct", sa.Float(), nullable=True),
        sa.Column("unique_count", sa.Integer(), nullable=True),
        sa.Column("sample_values", sa.Text(), nullable=True),
        sa.Column("code_map", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_columns_id", "dataset_columns", ["id"])
    op.create_index("ix_dataset_columns_dataset_id", "dataset_columns", ["dataset_id"])

    op.create_table(
        "dataset_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_rows_id", "dataset_rows", ["id"])
    op.create_index("ix_dataset_rows_dataset_id", "dataset_rows", ["dataset_id"])

    op.create_table(
        "surveys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("period", sa.String(), nullable=True),
        sa.Column("quarter", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("source_sheet", sa.String(), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=False),
        sa.Column("data_start_row", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_surveys_id", "surveys", ["id"])
    op.create_index("ix_surveys_dataset_id", "surveys", ["dataset_id"])
    op.create_index("ix_surveys_user_id", "surveys", ["user_id"])

    op.create_table(
        "survey_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("dataset_column_id", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(), nullable=False),
        sa.Column("question_no", sa.String(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(), nullable=True),
        sa.Column("scale_type", sa.String(), nullable=True),
        sa.Column("options", sa.Text(), nullable=True),
        sa.Column("is_likert", sa.Boolean(), nullable=True),
        sa.Column("is_demographic", sa.Boolean(), nullable=True),
        sa.Column("is_open_text", sa.Boolean(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"]),
        sa.ForeignKeyConstraint(["dataset_column_id"], ["dataset_columns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_survey_questions_id", "survey_questions", ["id"])
    op.create_index("ix_survey_questions_survey_id", "survey_questions", ["survey_id"])

    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("dataset_row_id", sa.Integer(), nullable=False),
        sa.Column("respondent_no", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"]),
        sa.ForeignKeyConstraint(["dataset_row_id"], ["dataset_rows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_survey_responses_id", "survey_responses", ["id"])
    op.create_index("ix_survey_responses_survey_id", "survey_responses", ["survey_id"])

    op.create_table(
        "survey_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("response_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("option_label", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["response_id"], ["survey_responses.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["survey_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_survey_answers_id", "survey_answers", ["id"])
    op.create_index("ix_survey_answers_response_id", "survey_answers", ["response_id"])
    op.create_index("ix_survey_answers_question_id", "survey_answers", ["question_id"])

    op.create_table(
        "survey_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metrics", sa.Text(), nullable=True),
        sa.Column("quality_issues", sa.Text(), nullable=True),
        sa.Column("ai_report", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_survey_reports_id", "survey_reports", ["id"])
    op.create_index("ix_survey_reports_survey_id", "survey_reports", ["survey_id"])


def downgrade() -> None:
    op.drop_table("survey_reports")
    op.drop_table("survey_answers")
    op.drop_table("survey_responses")
    op.drop_table("survey_questions")
    op.drop_table("surveys")
    op.drop_table("dataset_rows")
    op.drop_table("dataset_columns")
    op.drop_table("datasets")
    op.drop_table("data_analyses")
    op.drop_table("analyses")
    op.drop_table("users")
