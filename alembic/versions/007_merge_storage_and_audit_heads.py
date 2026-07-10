"""merge storage and audit heads

Revision ID: 007_merge_heads
Revises: 006_exam_file_storage, 9a5cbd7ee557
Create Date: 2026-07-07
"""

from typing import Sequence, Union


revision: str = "007_merge_heads"
down_revision: Union[tuple[str, str], None] = (
    "006_exam_file_storage",
    "9a5cbd7ee557",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
