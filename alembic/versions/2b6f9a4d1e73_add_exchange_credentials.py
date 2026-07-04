"""add_exchange_credentials

Revision ID: 2b6f9a4d1e73
Revises: 8f2b5a1d6c40
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b6f9a4d1e73'
down_revision: Union[str, Sequence[str], None] = '8f2b5a1d6c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'exchange_credentials',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('exchange', sa.String(length=20), nullable=False),
        sa.Column('api_key_encrypted', sa.String(length=500), nullable=False),
        sa.Column('api_secret_encrypted', sa.String(length=500), nullable=False),
        sa.Column('key_preview', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('exchange'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('exchange_credentials')
