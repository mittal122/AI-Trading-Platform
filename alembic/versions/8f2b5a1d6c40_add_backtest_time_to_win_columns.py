"""add_backtest_time_to_win_columns

Revision ID: 8f2b5a1d6c40
Revises: 1c9c073277cf
Create Date: 2026-07-02 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f2b5a1d6c40'
down_revision: Union[str, Sequence[str], None] = '1c9c073277cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('backtest_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('avg_candles_to_win', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('avg_time_to_win_display', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('backtest_runs', schema=None) as batch_op:
        batch_op.drop_column('avg_time_to_win_display')
        batch_op.drop_column('avg_candles_to_win')
