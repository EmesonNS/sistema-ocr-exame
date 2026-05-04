"""add_audit_fields

Revision ID: 9a5cbd7ee557
Revises: c720a2ebaaac
Create Date: 2026-05-03 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a5cbd7ee557'
down_revision: Union[str, None] = 'c720a2ebaaac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resultados_biomarcadores', sa.Column('is_human_verified', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('resultados_biomarcadores', sa.Column('verified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('resultados_biomarcadores', 'verified_at')
    op.drop_column('resultados_biomarcadores', 'is_human_verified')
