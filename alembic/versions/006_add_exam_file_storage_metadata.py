"""add_exam_file_storage_metadata

Adiciona metadados de storage persistente para o Arquivo de Exame Original.

Revision ID: 006_exam_file_storage
Revises: 005_add_clinical_summary
Create Date: 2026-07-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_exam_file_storage"
down_revision: Union[str, None] = "005_add_clinical_summary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exames", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("exames", sa.Column("storage_provider", sa.String(length=20), nullable=True))
    op.add_column("exames", sa.Column("storage_bucket", sa.String(length=255), nullable=True))
    op.add_column("exames", sa.Column("storage_object_key", sa.String(length=1024), nullable=True))
    op.add_column("exames", sa.Column("storage_content_type", sa.String(length=255), nullable=True))
    op.add_column("exames", sa.Column("storage_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("exames", sa.Column("storage_checksum", sa.String(length=128), nullable=True))
    op.add_column("exames", sa.Column("storage_status", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("exames", "storage_status")
    op.drop_column("exames", "storage_checksum")
    op.drop_column("exames", "storage_size_bytes")
    op.drop_column("exames", "storage_content_type")
    op.drop_column("exames", "storage_object_key")
    op.drop_column("exames", "storage_bucket")
    op.drop_column("exames", "storage_provider")
    op.drop_column("exames", "original_filename")
