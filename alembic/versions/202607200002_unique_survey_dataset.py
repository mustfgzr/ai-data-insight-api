"""Ensure one survey projection per dataset.

Revision ID: 202607200002
Revises: 202607200001
Create Date: 2026-07-20
"""

from alembic import op


revision = "202607200002"
down_revision = "202607200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.create_unique_constraint("uq_surveys_dataset_id", ["dataset_id"])


def downgrade() -> None:
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.drop_constraint("uq_surveys_dataset_id", type_="unique")
