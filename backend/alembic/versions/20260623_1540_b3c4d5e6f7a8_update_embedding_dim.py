"""update embedding dimension to 384

Revision ID: b3c4d5e6f7a8
Revises: 11ada0afc8ed
Create Date: 2026-06-23

Changes: document_chunks.embedding Vector(1536) → Vector(384)
to match sentence-transformers/all-MiniLM-L6-v2 output dimensions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = '11ada0afc8ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old column and recreate with new dimension
    # (pgvector does not support ALTER COLUMN type for vector columns directly)
    op.drop_column('document_chunks', 'embedding')
    op.add_column(
        'document_chunks',
        sa.Column('embedding', Vector(384), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('document_chunks', 'embedding')
    op.add_column(
        'document_chunks',
        sa.Column('embedding', Vector(1536), nullable=True)
    )
