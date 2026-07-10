"""add_api_key_rotation_versioning

Revision ID: 011_add_api_key_rotation_versioning
Revises: 010_add_loinc_mappings
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "011_add_api_key_rotation_versioning"
down_revision: Union[str, None] = "010_add_loinc_mappings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.add_column(
        "api_keys",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "api_keys",
        sa.Column("rotated_from_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_api_keys_rotated_from_id",
        "api_keys",
        "api_keys",
        ["rotated_from_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_api_keys_rotated_from_id", "api_keys", type_="foreignkey")
    op.drop_column("api_keys", "rotated_at")
    op.drop_column("api_keys", "rotated_from_id")
    op.drop_column("api_keys", "version")
