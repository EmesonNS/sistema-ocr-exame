"""add_loinc_mappings

Cria tabela de mapeamento LOINC e promove seed inicial a partir do mapa estático.
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.core.sa_types


revision: str = "010_add_loinc_mappings"
down_revision: Union[str, None] = "009_add_exame_created_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOINC_SEED = [
    {"keyword": "GLICOSE", "loinc_code": "2345-7", "description": "Glicose"},
    {"keyword": "HEMOGLOBINA", "loinc_code": "718-7", "description": "Hemoglobina"},
    {"keyword": "HEMATOCRITO", "loinc_code": "4544-3", "description": "Hematócrito"},
    {"keyword": "LEUCOCITOS", "loinc_code": "6690-2", "description": "Leucócitos"},
    {"keyword": "ERITROCITOS", "loinc_code": "789-8", "description": "Eritrócitos"},
    {"keyword": "PLAQUETAS", "loinc_code": "777-3", "description": "Plaquetas"},
    {"keyword": "COLESTEROL TOTAL", "loinc_code": "2093-3", "description": "Colesterol total"},
    {"keyword": "TRIGLICERIDEOS", "loinc_code": "2571-8", "description": "Triglicerídeos"},
    {"keyword": "HDL", "loinc_code": "2085-9", "description": "HDL"},
    {"keyword": "LDL", "loinc_code": "13457-7", "description": "LDL"},
    {"keyword": "VLDL", "loinc_code": "46986-6", "description": "VLDL"},
    {"keyword": "UREIA", "loinc_code": "22664-4", "description": "Ureia"},
    {"keyword": "CREATININA", "loinc_code": "2160-0", "description": "Creatinina"},
    {"keyword": "TGO", "loinc_code": "1920-8", "description": "TGO"},
    {"keyword": "TGP", "loinc_code": "1742-6", "description": "TGP"},
    {"keyword": "TSH", "loinc_code": "11579-0", "description": "TSH"},
    {"keyword": "T4 LIVRE", "loinc_code": "3024-7", "description": "T4 livre"},
]


def upgrade() -> None:
    op.create_table(
        "loinc_mappings",
        sa.Column("id", app.core.sa_types.GUID(), nullable=False),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("loinc_code", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keyword"),
    )
    op.create_index("ix_loinc_mappings_keyword", "loinc_mappings", ["keyword"], unique=True)
    op.create_index("ix_loinc_mappings_loinc_code", "loinc_mappings", ["loinc_code"], unique=False)

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO loinc_mappings (id, keyword, loinc_code, description) VALUES (:id, :keyword, :loinc_code, :description)"
        ),
        [
            {"id": uuid.uuid5(uuid.NAMESPACE_URL, f"loinc:{row['keyword']}"), **row}
            for row in LOINC_SEED
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_loinc_mappings_loinc_code", table_name="loinc_mappings")
    op.drop_index("ix_loinc_mappings_keyword", table_name="loinc_mappings")
    op.drop_table("loinc_mappings")
