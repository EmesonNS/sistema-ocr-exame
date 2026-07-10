"""add_ai_usage_metrics

Adiciona métricas de uso de IA ao exame para observabilidade de custo.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_add_ai_usage_metrics"
down_revision: Union[str, None] = "007_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exames", sa.Column("total_tokens", sa.Integer(), nullable=True))
    op.add_column("exames", sa.Column("agentic_zoom_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("exames", "agentic_zoom_tokens")
    op.drop_column("exames", "total_tokens")
