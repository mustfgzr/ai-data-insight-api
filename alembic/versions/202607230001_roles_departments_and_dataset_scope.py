"""Add user roles and shared department scope.

Revision ID: 202607230001
Revises: 202607210001
Create Date: 2026-07-23
"""

from __future__ import annotations

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "202607230001"
down_revision = "202607210001"
branch_labels = None
depends_on = None


def _department_key(value: str) -> str:
    display_name = " ".join(value.strip().split())
    normalized = unicodedata.normalize("NFKD", display_name)
    ascii_name = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_name).casefold().strip()


def _department_id(connection, name: str) -> int:
    display_name = " ".join(name.strip().split())
    key = _department_key(display_name)
    departments = sa.table(
        "departments",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("name_key", sa.String),
    )
    existing = connection.execute(
        sa.select(departments.c.id).where(departments.c.name_key == key)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    connection.execute(departments.insert().values(name=display_name, name_key=key))
    return connection.execute(
        sa.select(departments.c.id).where(departments.c.name_key == key)
    ).scalar_one()


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_key", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_key", name="uq_departments_name_key"),
    )
    op.create_index("ix_departments_id", "departments", ["id"])
    op.create_index("ix_departments_name_key", "departments", ["name_key"], unique=True)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("role", sa.String(), nullable=False, server_default="analyst"))
        batch_op.add_column(
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    with op.batch_alter_table("datasets") as batch_op:
        batch_op.add_column(sa.Column("department_id", sa.Integer(), nullable=True))

    connection = op.get_bind()
    connection.execute(sa.text("UPDATE users SET role = 'analyst' WHERE role IS NULL OR role = ''"))
    unassigned_id = _department_id(connection, "Atanmamis")
    connection.execute(
        sa.text("UPDATE datasets SET department_id = :department_id WHERE department_id IS NULL"),
        {"department_id": unassigned_id},
    )
    survey_departments = connection.execute(
        sa.text(
            "SELECT dataset_id, department FROM surveys "
            "WHERE department IS NOT NULL AND TRIM(department) != ''"
        )
    ).mappings()
    for survey in survey_departments:
        department_id = _department_id(connection, survey["department"])
        connection.execute(
            sa.text("UPDATE datasets SET department_id = :department_id WHERE id = :dataset_id"),
            {"department_id": department_id, "dataset_id": survey["dataset_id"]},
        )

    with op.batch_alter_table("datasets") as batch_op:
        batch_op.alter_column("department_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_datasets_department_id", "departments", ["department_id"], ["id"])
        batch_op.create_index("ix_datasets_department_id", ["department_id"])
        batch_op.create_index("ix_datasets_user_department", ["user_id", "department_id"])


def downgrade() -> None:
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.drop_index("ix_datasets_user_department")
        batch_op.drop_index("ix_datasets_department_id")
        batch_op.drop_constraint("fk_datasets_department_id", type_="foreignkey")
        batch_op.drop_column("department_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("must_change_password")
        batch_op.drop_column("role")
        batch_op.drop_column("full_name")

    op.drop_index("ix_departments_name_key", table_name="departments")
    op.drop_index("ix_departments_id", table_name="departments")
    op.drop_table("departments")
