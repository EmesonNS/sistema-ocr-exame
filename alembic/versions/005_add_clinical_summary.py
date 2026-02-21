"""add_clinical_summary_fields

Adiciona campos para armazenar resumo clínico gerado por IA.
Permite análise secundária dos biomarcadores extraídos.

Revision ID: 005_add_clinical_summary
Revises: 004_add_processing_progress
Create Date: 2026-02-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "005_add_clinical_summary"
down_revision: Union[str, None] = "004_add_processing_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Campo para armazenar o resumo clínico estruturado (JSON)
    op.add_column(
        "exames",
        sa.Column(
            "clinical_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Campo para timestamp de geração do resumo
    op.add_column(
        "exames",
        sa.Column(
            "summary_generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("exames", "summary_generated_at")
    op.drop_column("exames", "clinical_summary")
