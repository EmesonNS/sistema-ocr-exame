"""add_exame_created_at

Adiciona created_at aos exames para suportar política de retenção.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_add_exame_created_at"
down_revision: Union[str, None] = "008_add_ai_usage_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exames",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.alter_column("exames", "created_at", server_default=None)


def downgrade() -> None:
    op.drop_column("exames", "created_at")
