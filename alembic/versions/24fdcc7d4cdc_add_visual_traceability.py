"""add_visual_traceability

Revision ID: 24fdcc7d4cdc
Revises: c126e4eff94d
Create Date: 2026-05-03 20:20:06.831736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '24fdcc7d4cdc'
down_revision: Union[str, None] = 'c126e4eff94d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona colunas para rastreabilidade visual (Fase 7)
    op.add_column('resultados_biomarcadores', sa.Column('bounding_box', sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True))
    op.add_column('resultados_biomarcadores', sa.Column('page_number', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('resultados_biomarcadores', 'page_number')
    op.drop_column('resultados_biomarcadores', 'bounding_box')
