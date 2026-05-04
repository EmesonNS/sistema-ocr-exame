"""add_loinc_code

Revision ID: c720a2ebaaac
Revises: 24fdcc7d4cdc
Create Date: 2026-05-03 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c720a2ebaaac'
down_revision: Union[str, None] = '24fdcc7d4cdc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resultados_biomarcadores', sa.Column('loinc_code', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_resultados_biomarcadores_loinc_code'), 'resultados_biomarcadores', ['loinc_code'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_resultados_biomarcadores_loinc_code'), table_name='resultados_biomarcadores')
    op.drop_column('resultados_biomarcadores', 'loinc_code')
