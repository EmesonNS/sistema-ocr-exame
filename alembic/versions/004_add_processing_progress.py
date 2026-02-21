"""add_processing_progress_fields

Adiciona campos para feedback assíncrono de progresso do processamento.
Permite que usuários acompanhem cada etapa da análise de exames.

Revision ID: 004_add_processing_progress
Revises: 003_biomarker_norm
Create Date: 2026-02-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_add_processing_progress"
down_revision: Union[str, None] = "003_biomarker_norm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona campos de progress tracking à tabela exames

    # Campo para nome do estágio atual
    op.add_column(
        "exames",
        sa.Column("processing_stage", sa.String(50), nullable=True),
    )

    # Campo para percentual de progresso (0-100)
    op.add_column(
        "exames",
        sa.Column("processing_percent", sa.Integer(), nullable=True),
    )

    # Campo para mensagem legível do progresso
    op.add_column(
        "exames",
        sa.Column("processing_message", sa.String(500), nullable=True),
    )

    # Inicializa registros existentes com valores padrão
    op.execute("""
        UPDATE exames 
        SET 
            processing_stage = CASE 
                WHEN status_processamento = 'concluido' THEN 'completed'
                WHEN status_processamento = 'erro' THEN 'failed'
                WHEN status_processamento = 'processando' THEN 'ai_analyzing'
                ELSE 'queued'
            END,
            processing_percent = CASE 
                WHEN status_processamento = 'concluido' THEN 100
                WHEN status_processamento = 'erro' THEN 0
                WHEN status_processamento = 'processando' THEN 50
                ELSE 0
            END,
            processing_message = CASE 
                WHEN status_processamento = 'concluido' THEN 'Processamento concluído'
                WHEN status_processamento = 'erro' THEN 'Erro no processamento'
                WHEN status_processamento = 'processando' THEN 'Em processamento'
                ELSE 'Aguardando processamento'
            END
        WHERE processing_stage IS NULL
    """)


def downgrade() -> None:
    # Reverte alterações
    op.drop_column("exames", "processing_message")
    op.drop_column("exames", "processing_percent")
    op.drop_column("exames", "processing_stage")
