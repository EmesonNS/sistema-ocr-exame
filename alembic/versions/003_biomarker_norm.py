"""add_biomarker_normalization_fields

Adiciona campos para normalização determinística de biomarcadores.
Resolve problema de confusão entre valores percentuais e absolutos.

Revision ID: 003_biomarker_norm
Revises: 002_add_api_keys_table
Create Date: 2026-02-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_biomarker_norm"
down_revision: Union[str, None] = "002_add_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona novos campos à tabela resultados_biomarcadores

    # Campo para valor original do OCR
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("valor_raw", sa.String(200), nullable=True),
    )

    # Campo para valor numérico (para cálculos)
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("valor_numerico", sa.Numeric(10, 4), nullable=True),
    )

    # Campo para tipo do valor (absoluto/percentual/textual)
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("tipo_valor", sa.String(20), nullable=True),
    )

    # Referência parseada (min e max)
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("referencia_min", sa.Numeric(10, 4), nullable=True),
    )
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("referencia_max", sa.Numeric(10, 4), nullable=True),
    )

    # Campo para flag de revisão necessária
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("needs_review", sa.Boolean(), nullable=True, server_default="false"),
    )

    # Campo para descrição da correção aplicada
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("correcao_aplicada", sa.String(500), nullable=True),
    )

    # Campo para nível de confiança
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("confianca", sa.Float(), nullable=True, server_default="1.0"),
    )

    # Campo para fonte do valor (ocr/calculado/corrigido)
    op.add_column(
        "resultados_biomarcadores",
        sa.Column("fonte_valor", sa.String(50), nullable=True, server_default="ocr"),
    )

    # Altera coluna valor_extraido de Float para String (para suportar valores textuais)
    # Nota: em PostgreSQL, isso requer mais cuidado
    op.execute("""
        ALTER TABLE resultados_biomarcadores 
        ALTER COLUMN valor_extraido TYPE VARCHAR(100) 
        USING valor_extraido::VARCHAR(100)
    """)

    # Altera coluna unidade_medida para maior tamanho
    op.execute("""
        ALTER TABLE resultados_biomarcadores 
        ALTER COLUMN unidade_medida TYPE VARCHAR(50)
    """)

    # Altera status_alerta para tamanho maior e adiciona default
    op.execute("""
        ALTER TABLE resultados_biomarcadores 
        ALTER COLUMN status_alerta TYPE VARCHAR(20)
    """)
    op.execute("""
        UPDATE resultados_biomarcadores 
        SET status_alerta = 'indefinido' 
        WHERE status_alerta IS NULL
    """)

    # Atualiza campos novos com valores derivados dos existentes
    # (para migração suave de dados existentes)
    op.execute("""
        UPDATE resultados_biomarcadores 
        SET 
            valor_raw = valor_extraido,
            tipo_valor = CASE 
                WHEN unidade_medida LIKE '%%%%' THEN 'percentual'
                WHEN unidade_medida LIKE '%%/mm%%' THEN 'absoluto'
                ELSE 'absoluto'
            END,
            fonte_valor = 'ocr',
            needs_review = false,
            confianca = 1.0
        WHERE valor_raw IS NULL
    """)


def downgrade() -> None:
    # Reverte alterações
    op.drop_column("resultados_biomarcadores", "fonte_valor")
    op.drop_column("resultados_biomarcadores", "confianca")
    op.drop_column("resultados_biomarcadores", "correcao_aplicada")
    op.drop_column("resultados_biomarcadores", "needs_review")
    op.drop_column("resultados_biomarcadores", "referencia_max")
    op.drop_column("resultados_biomarcadores", "referencia_min")
    op.drop_column("resultados_biomarcadores", "tipo_valor")
    op.drop_column("resultados_biomarcadores", "valor_numerico")
    op.drop_column("resultados_biomarcadores", "valor_raw")

    # Reverte valor_extraido para Float
    op.execute("""
        ALTER TABLE resultados_biomarcadores 
        ALTER COLUMN valor_extraido TYPE FLOAT 
        USING valor_extraido::FLOAT
    """)
