"""add image worker operations

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for operation in (
        "PNG_TO_JPEG",
        "PNG_TO_WEBP",
        "WEBP_TO_PNG",
        "WEBP_TO_JPEG",
        "JPEG_TO_WEBP",
        "DOWNSAMPLE",
    ):
        op.execute(f"ALTER TYPE operation ADD VALUE IF NOT EXISTS '{operation}'")


def downgrade() -> None:
    pass